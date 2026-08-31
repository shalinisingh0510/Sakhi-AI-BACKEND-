import logging
import os
import tempfile
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.services.auth import StoredUser
from app.services.voice_service import get_stt_service, SpeechToTextService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Voice"])

class TranscriptionResponse(BaseModel):
    text: str
    language: str | None = None

ALLOWED_MIME_TYPES = {
    "audio/webm", "audio/mp4", "audio/mpeg", 
    "audio/ogg", "audio/wav", "audio/x-m4a",
    "video/mp4" # some browsers send m4a as video/mp4
}
ALLOWED_EXTENSIONS = {".webm", ".mp4", ".mp3", ".ogg", ".wav", ".m4a"}

@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transcribe audio to text",
)
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str | None = Form(None),
    current_user: StoredUser = Depends(get_current_user),
    stt_service: SpeechToTextService = Depends(get_stt_service),
):
    settings = get_settings()

    # 1. Validate Language
    if language and language not in settings.stt_supported_languages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {language}. Supported: {settings.stt_supported_languages}"
        )

    # 2. Validate MIME type
    if file.content_type not in ALLOWED_MIME_TYPES:
        logger.warning(f"Unsupported audio MIME type: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported audio format."
        )

    # 3. Save to temporary file securely
    temp_file_path = ""
    try:
        # Read file chunks to enforce size limit
        file_size = 0
        max_bytes = settings.stt_max_audio_size_mb * 1024 * 1024
        
        fd, temp_file_path = tempfile.mkstemp(suffix=".webm")
        with open(temp_file_path, "wb") as out_file:
            while chunk := await file.read(8192):
                file_size += len(chunk)
                if file_size > max_bytes:
                    os.close(fd)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Audio file exceeds {settings.stt_max_audio_size_mb} MB limit."
                    )
                out_file.write(chunk)
        os.close(fd)
        
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Audio file is empty."
            )

        # 4. Transcribe using STT Service
        transcript = stt_service.transcribe(
            audio_file_path=temp_file_path,
            filename=file.filename or "audio.webm",
            language=language
        )

        return TranscriptionResponse(text=transcript, language=language)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during audio transcription: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transcription failed due to an internal error."
        )
    finally:
        # 5. Always delete the temporary file!
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except OSError as e:
                logger.error(f"Failed to delete temp audio file {temp_file_path}: {e}")

