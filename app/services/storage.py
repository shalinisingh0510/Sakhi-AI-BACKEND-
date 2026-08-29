from __future__ import annotations

import logging
from typing import Protocol

from app.core.config import Settings

logger = logging.getLogger(__name__)


class StorageServiceProtocol(Protocol):
    def generate_presigned_upload_url(self, object_key: str, content_type: str, expiration_seconds: int = 3600) -> str: ...
    
    def generate_presigned_download_url(self, object_key: str, expiration_seconds: int = 3600) -> str: ...
    
    def delete_object(self, object_key: str) -> None: ...


class CloudflareStorageService:
    def __init__(self, settings: Settings) -> None:
        self.bucket_name = settings.cloudflare_r2_bucket_name
        self.client = None

        if not settings.cloudflare_r2_endpoint_url or not settings.cloudflare_r2_access_key_id or not settings.cloudflare_r2_secret_access_key or not settings.cloudflare_r2_bucket_name:
            logger.warning("Cloudflare R2 is not fully configured. Storage operations will fail.")
            return

        try:
            import boto3
            from botocore.config import Config

            self.client = boto3.client(
                "s3",
                endpoint_url=settings.cloudflare_r2_endpoint_url,
                aws_access_key_id=settings.cloudflare_r2_access_key_id,
                aws_secret_access_key=settings.cloudflare_r2_secret_access_key.get_secret_value() if settings.cloudflare_r2_secret_access_key else None,
                config=Config(signature_version="s3v4"),
                region_name="auto",
            )
        except ImportError:
            logger.warning("boto3 is not installed. Storage operations will not be available.")

    def generate_presigned_upload_url(self, object_key: str, content_type: str, expiration_seconds: int = 3600) -> str:
        if not self.bucket_name or not self.client:
            raise RuntimeError("Cloudflare R2 bucket name or boto3 client is not configured.")

        try:
            response = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": object_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expiration_seconds,
            )
            return response
        except Exception as e:
            logger.exception(f"Error generating presigned upload URL for {object_key}")
            raise RuntimeError("Failed to generate upload URL") from e

    def generate_presigned_download_url(self, object_key: str, expiration_seconds: int = 3600) -> str:
        if not self.bucket_name or not self.client:
            raise RuntimeError("Cloudflare R2 bucket name or boto3 client is not configured.")

        try:
            response = self.client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": object_key,
                },
                ExpiresIn=expiration_seconds,
            )
            return response
        except Exception as e:
            logger.exception(f"Error generating presigned download URL for {object_key}")
            raise RuntimeError("Failed to generate download URL") from e

    def delete_object(self, object_key: str) -> None:
        if not self.bucket_name or not self.client:
            raise RuntimeError("Cloudflare R2 bucket name or boto3 client is not configured.")
        
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_key)
        except Exception as e:
            logger.exception(f"Error deleting object {object_key} from R2")
            raise RuntimeError("Failed to delete object") from e
