"""
Assets API routes for managing file uploads and downloads.

This module provides FastAPI routes for:
- Generating presigned upload URLs
- Retrieving asset details
- Deleting assets
- Creating ZIP downloads
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import JSONResponse

from app.models.schemas import (
    UploadUrlRequest,
    UploadUrlResponse,
    AssetResponse,
    AssetDeleteResponse,
    ZipDownloadRequest,
    ZipDownloadResponse,
    CharacterAssetsRequest,
    AssetErrorResponse,
    AssetCategory,
)
from app.services.storage import (
    get_storage_service,
    StorageService,
    StorageError,
    FileNotFoundError as StorageFileNotFoundError,
)
from app.services.asset_utils import (
    validate_file_type,
    ValidationError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assets", tags=["assets"])


# ============================================================================
# Dependency Injection
# ============================================================================

def get_storage() -> StorageService:
    """Dependency to get storage service instance."""
    return get_storage_service()


# Placeholder for auth dependency - to be implemented by auth workstream
async def get_current_user():
    """
    Get the current authenticated user.

    This is a placeholder that should be replaced with actual auth
    implementation from Workstream 1.
    """
    # TODO: Replace with actual auth implementation
    return {"id": "placeholder_user_id", "email": "user@example.com"}


async def require_auth(current_user = Depends(get_current_user)):
    """Dependency that requires authentication."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return current_user


# ============================================================================
# Routes
# ============================================================================

@router.post(
    "/upload-url",
    response_model=UploadUrlResponse,
    status_code=status.HTTP_200_OK,
    summary="Get presigned upload URL",
    description="Generate a presigned URL for direct file upload to storage.",
    responses={
        400: {"model": AssetErrorResponse, "description": "Invalid request"},
        401: {"description": "Unauthorized"},
        500: {"model": AssetErrorResponse, "description": "Server error"},
    }
)
async def get_upload_url(
    request: UploadUrlRequest,
    current_user = Depends(require_auth),
    storage: StorageService = Depends(get_storage)
) -> UploadUrlResponse:
    """
    Generate a presigned URL for uploading a file.

    The client should use the returned URL and fields to upload the file
    directly to storage using a POST request with form-data.
    """
    try:
        # Validate file type
        validate_file_type(request.filename, request.content_type)

        # Determine prefix based on category
        prefix_map = {
            AssetCategory.CHARACTER: "characters",
            AssetCategory.ANIMATION: "animations",
            AssetCategory.THUMBNAIL: "thumbnails",
            AssetCategory.OTHER: "misc",
        }
        prefix = prefix_map.get(request.category, "misc")

        # Add user ID to prefix for organization
        prefix = f"{prefix}/{current_user['id']}"

        # Generate upload URL
        result = await storage.generate_upload_url(
            filename=request.filename,
            content_type=request.content_type,
            prefix=prefix
        )

        return UploadUrlResponse(
            upload_url=result["upload_url"],
            fields=result["fields"],
            key=result["key"],
            public_url=result["public_url"],
            expires_in=result["expires_in"]
        )

    except ValidationError as e:
        logger.warning(f"Upload URL validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except StorageError as e:
        logger.error(f"Storage error generating upload URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL"
        )


@router.get(
    "/{asset_id:path}",
    response_model=AssetResponse,
    summary="Get asset details",
    description="Retrieve details and download URL for an asset.",
    responses={
        404: {"model": AssetErrorResponse, "description": "Asset not found"},
        401: {"description": "Unauthorized"},
        500: {"model": AssetErrorResponse, "description": "Server error"},
    }
)
async def get_asset(
    asset_id: str,
    include_download_url: bool = Query(
        default=True,
        description="Include a signed download URL"
    ),
    download_expires_in: int = Query(
        default=3600,
        ge=60,
        le=86400,
        description="Download URL expiration in seconds"
    ),
    current_user = Depends(require_auth),
    storage: StorageService = Depends(get_storage)
) -> AssetResponse:
    """
    Get details for a specific asset.

    The asset_id is the storage key of the asset.
    """
    try:
        # Get asset info from storage
        asset_info = await storage.get_asset_info(asset_id)

        # Generate download URL if requested
        download_url = None
        if include_download_url:
            download_url = await storage.get_signed_url(
                asset_id,
                expires_in=download_expires_in
            )

        # Extract filename from key
        filename = asset_id.rsplit("/", 1)[-1] if "/" in asset_id else asset_id

        # Determine category from path
        category = AssetCategory.OTHER
        if asset_id.startswith("characters"):
            category = AssetCategory.CHARACTER
        elif asset_id.startswith("animations"):
            category = AssetCategory.ANIMATION
        elif asset_id.startswith("thumbnails"):
            category = AssetCategory.THUMBNAIL

        # Note: In a full implementation, this would fetch additional metadata
        # from the database. For now, we return storage-based info.
        return AssetResponse(
            id=asset_id,
            user_id=current_user["id"],  # Would come from DB
            storage_key=asset_id,
            filename=filename,
            content_type=asset_info.get("content_type", "application/octet-stream"),
            size_bytes=asset_info.get("size", 0),
            category=category,
            public_url=asset_info.get("public_url", ""),
            download_url=download_url,
            metadata=asset_info.get("metadata"),
            created_at=asset_info.get("last_modified", "1970-01-01T00:00:00"),
        )

    except StorageFileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    except StorageError as e:
        logger.error(f"Storage error getting asset {asset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve asset"
        )


@router.delete(
    "/{asset_id:path}",
    response_model=AssetDeleteResponse,
    summary="Delete an asset",
    description="Delete an asset from storage.",
    responses={
        404: {"model": AssetErrorResponse, "description": "Asset not found"},
        401: {"description": "Unauthorized"},
        500: {"model": AssetErrorResponse, "description": "Server error"},
    }
)
async def delete_asset(
    asset_id: str,
    current_user = Depends(require_auth),
    storage: StorageService = Depends(get_storage)
) -> AssetDeleteResponse:
    """
    Delete a specific asset.

    The asset_id is the storage key of the asset.
    Only the owner of the asset can delete it.
    """
    try:
        # Verify asset exists
        await storage.get_asset_info(asset_id)

        # TODO: Verify ownership when database integration is complete
        # For now, we proceed with deletion

        # Delete the asset
        await storage.delete_asset(asset_id)

        logger.info(f"Asset deleted: {asset_id} by user {current_user['id']}")

        return AssetDeleteResponse(
            id=asset_id,
            message="Asset deleted successfully"
        )

    except StorageFileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )
    except StorageError as e:
        logger.error(f"Storage error deleting asset {asset_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete asset"
        )


@router.post(
    "/download-zip",
    response_model=ZipDownloadResponse,
    summary="Create ZIP download",
    description="Create a ZIP file containing multiple assets.",
    responses={
        400: {"model": AssetErrorResponse, "description": "Invalid request"},
        401: {"description": "Unauthorized"},
        500: {"model": AssetErrorResponse, "description": "Server error"},
    }
)
async def create_zip_download(
    request: ZipDownloadRequest,
    current_user = Depends(require_auth),
    storage: StorageService = Depends(get_storage)
) -> ZipDownloadResponse:
    """
    Create a ZIP file containing the specified assets.

    Returns a signed URL for downloading the ZIP file.
    """
    try:
        # Verify at least one asset exists
        valid_assets = []
        total_size = 0

        for asset_id in request.asset_ids:
            try:
                info = await storage.get_asset_info(asset_id)
                valid_assets.append(asset_id)
                total_size += info.get("size", 0)
            except StorageFileNotFoundError:
                logger.warning(f"Asset not found for ZIP: {asset_id}")
                continue

        if not valid_assets:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid assets found"
            )

        # Create ZIP download
        download_url = await storage.create_zip_download(
            valid_assets,
            zip_filename=request.filename or "assets.zip"
        )

        return ZipDownloadResponse(
            download_url=download_url,
            expires_in=3600,
            file_count=len(valid_assets),
            total_size_bytes=total_size
        )

    except HTTPException:
        raise
    except StorageError as e:
        logger.error(f"Storage error creating ZIP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ZIP download"
        )


@router.post(
    "/download-all/{character_id}",
    response_model=ZipDownloadResponse,
    summary="Download all character assets",
    description="Create a ZIP file containing all assets for a character.",
    responses={
        400: {"model": AssetErrorResponse, "description": "Invalid request"},
        404: {"model": AssetErrorResponse, "description": "Character not found"},
        401: {"description": "Unauthorized"},
        500: {"model": AssetErrorResponse, "description": "Server error"},
    }
)
async def download_character_assets(
    character_id: str,
    include_thumbnails: bool = Query(
        default=False,
        description="Include thumbnail images"
    ),
    current_user = Depends(require_auth),
    storage: StorageService = Depends(get_storage)
) -> ZipDownloadResponse:
    """
    Create a ZIP file containing all assets for a character.

    This includes the character image and all generated animations.
    """
    try:
        asset_ids = []
        total_size = 0

        # Find character assets
        # Note: This assumes assets are organized with character_id in the path
        # In a full implementation, this would query the database

        prefixes_to_search = [f"characters/{current_user['id']}"]
        if include_thumbnails:
            prefixes_to_search.append(f"thumbnails/{current_user['id']}")

        # Search animations
        prefixes_to_search.append(f"animations/{current_user['id']}")

        for prefix in prefixes_to_search:
            try:
                result = await storage.list_assets(prefix=prefix)
                for asset in result.get("assets", []):
                    # Filter by character_id in filename or path
                    if character_id in asset["key"]:
                        asset_ids.append(asset["key"])
                        total_size += asset.get("size", 0)
            except Exception as e:
                logger.warning(f"Error searching prefix {prefix}: {e}")

        if not asset_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No assets found for character"
            )

        # Create ZIP
        zip_filename = f"character_{character_id}_assets.zip"
        download_url = await storage.create_zip_download(
            asset_ids,
            zip_filename=zip_filename
        )

        return ZipDownloadResponse(
            download_url=download_url,
            expires_in=3600,
            file_count=len(asset_ids),
            total_size_bytes=total_size
        )

    except HTTPException:
        raise
    except StorageError as e:
        logger.error(f"Storage error creating character ZIP: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create ZIP download"
        )


@router.get(
    "/list/{category}",
    summary="List assets by category",
    description="List all assets in a category for the current user.",
    responses={
        401: {"description": "Unauthorized"},
        500: {"model": AssetErrorResponse, "description": "Server error"},
    }
)
async def list_assets(
    category: AssetCategory,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user = Depends(require_auth),
    storage: StorageService = Depends(get_storage)
):
    """
    List assets by category for the current user.
    """
    try:
        # Map category to prefix
        prefix_map = {
            AssetCategory.CHARACTER: "characters",
            AssetCategory.ANIMATION: "animations",
            AssetCategory.THUMBNAIL: "thumbnails",
            AssetCategory.OTHER: "misc",
        }
        prefix = f"{prefix_map[category]}/{current_user['id']}"

        # Get assets
        result = await storage.list_assets(
            prefix=prefix,
            max_keys=page_size
        )

        assets = result.get("assets", [])

        return {
            "assets": assets,
            "total": len(assets),
            "page": page,
            "page_size": page_size,
            "has_more": result.get("next_token") is not None
        }

    except StorageError as e:
        logger.error(f"Storage error listing assets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list assets"
        )
