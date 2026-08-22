from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MediaUploadRequest(BaseModel):
    filename: str = Field(..., description="The name of the file to be uploaded.")
    content_type: str = Field(..., description="The MIME type of the file (e.g., 'video/mp4', 'audio/mpeg').")
    size_bytes: int = Field(..., description="The size of the file in bytes.")


class MediaResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MediaUploadResponse(BaseModel):
    upload_url: str = Field(..., description="The pre-signed URL to upload the file to directly.")
    storage_key: str = Field(..., description="The internal storage key for the file.")
    media: MediaResponse
