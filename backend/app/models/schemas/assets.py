"""
Pydantic schemas for asset management.

This module defines request/response schemas for the assets API.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AssetType(str, Enum):
    """Types of assets that can be stored."""
    IMAGE = "image"
    VIDEO = "video"
    GIF = "gif"
    THUMBNAIL = "thumbnail"


class AssetCategory(str, Enum):
    """Categories for asset organization."""
    CHARACTER = "character"
    ANIMATION = "animation"
    THUMBNAIL = "thumbnail"
    OTHER = "other"


# ============================================================================
# Request Schemas
# ============================================================================

class UploadUrlRequest(BaseModel):
    """Request for generating a presigned upload URL."""

    filename: str = Field(
        ...,
        description="Original filename with extension",
        min_length=1,
        max_length=255
    )
    content_type: str = Field(
        ...,
        description="MIME type of the file",
        examples=["image/png", "image/gif", "video/mp4"]
    )
    category: AssetCategory = Field(
        default=AssetCategory.OTHER,
        description="Asset category for organization"
    )
    character_id: Optional[str] = Field(
        default=None,
        description="Associated character ID (if applicable)"
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Ensure filename has an extension."""
        if "." not in v:
            raise ValueError("Filename must include an extension")
        # Basic sanitization
        v = v.replace("/", "_").replace("\\", "_")
        return v

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        """Validate content type format."""
        allowed_types = [
            "image/png", "image/jpeg", "image/gif", "image/webp",
            "video/mp4", "video/webm"
        ]
        if v not in allowed_types:
            raise ValueError(f"Content type must be one of: {', '.join(allowed_types)}")
        return v


class AssetCreate(BaseModel):
    """Schema for creating a new asset record in the database."""

    user_id: str = Field(..., description="ID of the user who owns the asset")
    storage_key: str = Field(..., description="Storage key/path of the asset")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of the file")
    size_bytes: int = Field(..., description="File size in bytes", ge=0)
    category: AssetCategory = Field(
        default=AssetCategory.OTHER,
        description="Asset category"
    )
    character_id: Optional[str] = Field(
        default=None,
        description="Associated character ID"
    )
    animation_id: Optional[str] = Field(
        default=None,
        description="Associated animation ID"
    )
    width: Optional[int] = Field(
        default=None,
        description="Image/video width in pixels"
    )
    height: Optional[int] = Field(
        default=None,
        description="Image/video height in pixels"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Additional metadata"
    )


class AssetUpdate(BaseModel):
    """Schema for updating an asset record."""

    filename: Optional[str] = Field(default=None, description="New filename")
    metadata: Optional[dict] = Field(default=None, description="Updated metadata")


class ZipDownloadRequest(BaseModel):
    """Request for creating a ZIP download of multiple assets."""

    asset_ids: list[str] = Field(
        ...,
        description="List of asset IDs to include in ZIP",
        min_length=1,
        max_length=100
    )
    filename: Optional[str] = Field(
        default="assets.zip",
        description="Filename for the ZIP download"
    )


class CharacterAssetsRequest(BaseModel):
    """Request for downloading all assets for a character."""

    include_thumbnails: bool = Field(
        default=False,
        description="Whether to include thumbnail images"
    )


# ============================================================================
# Response Schemas
# ============================================================================

class UploadUrlResponse(BaseModel):
    """Response containing presigned upload URL and metadata."""

    upload_url: str = Field(..., description="URL for uploading the file")
    fields: dict = Field(
        ...,
        description="Form fields to include with the upload"
    )
    key: str = Field(..., description="Storage key for the uploaded file")
    public_url: str = Field(
        ...,
        description="Public URL where file will be accessible after upload"
    )
    expires_in: int = Field(..., description="Seconds until upload URL expires")


class AssetResponse(BaseModel):
    """Response containing asset details."""

    id: str = Field(..., description="Unique asset identifier")
    user_id: str = Field(..., description="ID of the asset owner")
    storage_key: str = Field(..., description="Storage key/path")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type")
    size_bytes: int = Field(..., description="File size in bytes")
    category: AssetCategory = Field(..., description="Asset category")
    public_url: str = Field(..., description="Public URL for accessing the asset")
    download_url: Optional[str] = Field(
        default=None,
        description="Signed download URL (if requested)"
    )
    character_id: Optional[str] = Field(default=None, description="Associated character ID")
    animation_id: Optional[str] = Field(default=None, description="Associated animation ID")
    width: Optional[int] = Field(default=None, description="Width in pixels")
    height: Optional[int] = Field(default=None, description="Height in pixels")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    """Response containing a list of assets."""

    assets: list[AssetResponse] = Field(..., description="List of assets")
    total: int = Field(..., description="Total number of assets")
    page: int = Field(default=1, description="Current page number")
    page_size: int = Field(default=20, description="Number of items per page")
    has_more: bool = Field(default=False, description="Whether more pages exist")


class ZipDownloadResponse(BaseModel):
    """Response containing ZIP download URL."""

    download_url: str = Field(..., description="Signed URL for downloading the ZIP")
    expires_in: int = Field(..., description="Seconds until download URL expires")
    file_count: int = Field(..., description="Number of files in the ZIP")
    total_size_bytes: Optional[int] = Field(
        default=None,
        description="Estimated total size of ZIP"
    )


class AssetDeleteResponse(BaseModel):
    """Response confirming asset deletion."""

    id: str = Field(..., description="ID of deleted asset")
    message: str = Field(default="Asset deleted successfully")


class StorageStatsResponse(BaseModel):
    """Response containing storage statistics."""

    total_files: int = Field(..., description="Total number of files")
    total_size_bytes: int = Field(..., description="Total size in bytes")
    total_size_mb: float = Field(..., description="Total size in megabytes")
    total_size_gb: float = Field(..., description="Total size in gigabytes")
    by_category: dict = Field(..., description="Statistics broken down by category")


class UploadCompleteRequest(BaseModel):
    """Request to confirm upload completion and create asset record."""

    key: str = Field(..., description="Storage key from upload URL response")
    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="MIME type of uploaded file")
    size_bytes: int = Field(..., description="Size of uploaded file", ge=0)
    category: AssetCategory = Field(
        default=AssetCategory.OTHER,
        description="Asset category"
    )
    character_id: Optional[str] = Field(default=None, description="Associated character ID")
    animation_id: Optional[str] = Field(default=None, description="Associated animation ID")
    width: Optional[int] = Field(default=None, description="Image width")
    height: Optional[int] = Field(default=None, description="Image height")
    metadata: Optional[dict] = Field(default=None, description="Additional metadata")


# ============================================================================
# Error Response Schema
# ============================================================================

class AssetErrorResponse(BaseModel):
    """Error response for asset operations."""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    code: Optional[str] = Field(default=None, description="Error code for programmatic handling")
