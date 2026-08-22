from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.requests import Request

from app.api.dependencies import get_current_user
from app.schemas.media import MediaResponse, MediaUploadRequest, MediaUploadResponse
from app.services.auth import StoredUser
from app.services.media import MediaNotFoundError, MediaService

router = APIRouter(prefix="/media", tags=["Media"])


def get_media_service(request: Request) -> MediaService:
    return request.app.state.media_service


@router.post(
    "/presigned-url",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a pre-signed URL for direct upload",
)
def generate_presigned_url(
    payload: MediaUploadRequest,
    current_user: StoredUser = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
) -> Any:
    """
    Generate a pre-signed Cloudflare R2 URL for uploading a media file directly from the client.
    This creates a database record to track the upload.
    """
    try:
        result = media_service.generate_upload_url(
            uploader_id=current_user.id,
            filename=payload.filename,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
        )
        return {
            "upload_url": result["upload_url"],
            "storage_key": result["storage_key"],
            "media": result["media_record"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {str(e)}",
        )


@router.get(
    "/",
    response_model=list[MediaResponse],
    summary="List user's uploaded media",
)
def list_media(
    current_user: StoredUser = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
) -> Any:
    """
    List all media files uploaded by the authenticated user.
    """
    return media_service.get_user_media(current_user.id)


@router.get(
    "/{media_id}/url",
    response_model=dict[str, str],
    summary="Get a pre-signed download URL for a media file",
)
def get_media_download_url(
    media_id: str,
    current_user: StoredUser = Depends(get_current_user),
    media_service: MediaService = Depends(get_media_service),
) -> Any:
    """
    Generate a pre-signed Cloudflare R2 URL to download or stream a media file.
    """
    try:
        # First ensure the user owns it, or it's part of a lesson they can access.
        # For simplicity, we just check ownership or assume media is public to authenticated users.
        url = media_service.get_media_url(media_id)
        return {"url": url}
    except MediaNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}",
        )
