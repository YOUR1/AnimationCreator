"""
Storage configuration for S3-compatible storage (DigitalOcean Spaces, AWS S3, etc.)

This module provides configuration and client setup for S3-compatible object storage.
"""

import os
import logging
from functools import lru_cache
from typing import Optional

import boto3
from botocore.config import Config
from pydantic import Field
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class StorageSettings(BaseSettings):
    """Storage configuration settings loaded from environment variables."""

    # Storage mode: 'local' for development, 's3' for production
    storage_mode: str = Field(default="local", alias="STORAGE_MODE")

    # Local storage settings (for development)
    local_storage_path: str = Field(default="/app/uploads", alias="LOCAL_STORAGE_PATH")
    local_storage_url: str = Field(default="http://localhost:3131/uploads", alias="LOCAL_STORAGE_URL")

    # S3-compatible storage settings
    storage_access_key: str = Field(default="", alias="STORAGE_ACCESS_KEY")
    storage_secret_key: str = Field(default="", alias="STORAGE_SECRET_KEY")
    storage_bucket_name: str = Field(default="animation-creator-assets", alias="STORAGE_BUCKET_NAME")
    storage_region: str = Field(default="nyc3", alias="STORAGE_REGION")
    storage_endpoint_url: str = Field(
        default="https://nyc3.digitaloceanspaces.com",
        alias="STORAGE_ENDPOINT_URL"
    )

    # CDN configuration
    cdn_enabled: bool = Field(default=True, alias="CDN_ENABLED")
    cdn_url: Optional[str] = Field(default=None, alias="CDN_URL")

    # Upload settings
    max_upload_size_mb: int = Field(default=100, alias="MAX_UPLOAD_SIZE_MB")
    allowed_content_types: list[str] = Field(
        default=[
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
            "video/mp4",
            "video/webm",
        ],
        alias="ALLOWED_CONTENT_TYPES"
    )

    # Signed URL settings
    default_signed_url_expiration: int = Field(default=3600, alias="DEFAULT_SIGNED_URL_EXPIRATION")
    upload_url_expiration: int = Field(default=900, alias="UPLOAD_URL_EXPIRATION")

    # Asset paths
    characters_path: str = Field(default="characters", alias="CHARACTERS_PATH")
    animations_path: str = Field(default="animations", alias="ANIMATIONS_PATH")
    thumbnails_path: str = Field(default="thumbnails", alias="THUMBNAILS_PATH")
    temp_path: str = Field(default="temp", alias="TEMP_PATH")

    class Config:
        env_file = ".env"
        extra = "ignore"

    @property
    def max_upload_size_bytes(self) -> int:
        """Get maximum upload size in bytes."""
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def public_url_base(self) -> str:
        """Get the base URL for public asset access."""
        if self.cdn_enabled and self.cdn_url:
            return self.cdn_url.rstrip("/")
        # Construct default DigitalOcean Spaces URL
        return f"https://{self.storage_bucket_name}.{self.storage_region}.digitaloceanspaces.com"


@lru_cache()
def get_storage_settings() -> StorageSettings:
    """Get cached storage settings instance."""
    return StorageSettings()


def create_s3_client():
    """
    Create and return a configured boto3 S3 client.

    Returns:
        boto3.client: Configured S3 client for the storage backend
    """
    settings = get_storage_settings()

    if not settings.storage_access_key or not settings.storage_secret_key:
        logger.warning(
            "Storage credentials not configured. "
            "Set STORAGE_ACCESS_KEY and STORAGE_SECRET_KEY environment variables."
        )

    # Configure retry behavior
    config = Config(
        retries={
            "max_attempts": 3,
            "mode": "adaptive"
        },
        signature_version="s3v4",
        s3={
            "addressing_style": "virtual"
        }
    )

    client = boto3.client(
        "s3",
        region_name=settings.storage_region,
        endpoint_url=settings.storage_endpoint_url,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        config=config
    )

    logger.info(
        f"S3 client created for endpoint: {settings.storage_endpoint_url}, "
        f"bucket: {settings.storage_bucket_name}"
    )

    return client


def get_s3_client():
    """
    Get the S3 client instance.

    Returns:
        boto3.client: S3 client instance
    """
    return create_s3_client()


def verify_bucket_access() -> bool:
    """
    Verify that the configured bucket is accessible.

    Returns:
        bool: True if bucket is accessible, False otherwise
    """
    settings = get_storage_settings()
    client = get_s3_client()

    try:
        client.head_bucket(Bucket=settings.storage_bucket_name)
        logger.info(f"Successfully verified access to bucket: {settings.storage_bucket_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to access bucket {settings.storage_bucket_name}: {e}")
        return False
