"""
Storage service for managing assets in S3-compatible storage or local filesystem.

This module provides async functions for uploading, downloading, and managing
files in S3-compatible storage (DigitalOcean Spaces, AWS S3, etc.) or local
filesystem for development.
"""

import io
import logging
import os
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.core.storage_config import (
    get_s3_client,
    get_storage_settings,
    StorageSettings,
)

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class FileNotFoundError(StorageError):
    """Raised when a file is not found in storage."""
    pass


class UploadError(StorageError):
    """Raised when a file upload fails."""
    pass


class LocalStorageService:
    """
    Local filesystem storage service for development.

    Stores files in a local directory and serves them via the backend.
    """

    def __init__(self):
        self.settings: StorageSettings = get_storage_settings()
        self.storage_path = Path(self.settings.local_storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def _generate_asset_key(self, filename: str, prefix: str = "") -> str:
        """Generate a unique storage key for an asset."""
        unique_id = uuid.uuid4().hex[:12]
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")

        ext = ""
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower()

        if prefix:
            return f"{prefix}/{timestamp}/{unique_id}{ext}"
        return f"{timestamp}/{unique_id}{ext}"

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        prefix: str = "",
        metadata: Optional[dict] = None
    ) -> str:
        """Upload a file to local storage."""
        file_size = len(file_bytes)
        if file_size > self.settings.max_upload_size_bytes:
            raise UploadError(
                f"File size ({file_size} bytes) exceeds maximum allowed "
                f"({self.settings.max_upload_size_bytes} bytes)"
            )

        key = self._generate_asset_key(filename, prefix)
        file_path = self.storage_path / key

        # Create directory structure
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        logger.info(f"Successfully uploaded file locally: {key}")

        # Return URL
        return f"{self.settings.local_storage_url}/{key}"

    async def get_signed_url(
        self,
        asset_id: str,
        expires_in: int = 3600,
        method: str = "get_object"
    ) -> str:
        """For local storage, just return the direct URL."""
        return f"{self.settings.local_storage_url}/{asset_id}"

    async def delete_asset(self, asset_id: str) -> None:
        """Delete an asset from local storage."""
        file_path = self.storage_path / asset_id
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Successfully deleted local asset: {asset_id}")

    async def get_asset_info(self, asset_id: str) -> dict:
        """Get metadata about a local asset."""
        file_path = self.storage_path / asset_id
        if not file_path.exists():
            raise FileNotFoundError(f"Asset not found: {asset_id}")

        stat = file_path.stat()
        return {
            "key": asset_id,
            "size": stat.st_size,
            "content_type": "application/octet-stream",
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "metadata": {},
            "public_url": f"{self.settings.local_storage_url}/{asset_id}"
        }


class StorageService:
    """
    Service for managing file storage operations.

    Provides methods for uploading, downloading, and managing files
    in S3-compatible storage.
    """

    def __init__(self):
        self.settings: StorageSettings = get_storage_settings()
        self._client = None

    @property
    def client(self):
        """Get or create S3 client."""
        if self._client is None:
            self._client = get_s3_client()
        return self._client

    def _generate_asset_key(self, filename: str, prefix: str = "") -> str:
        """
        Generate a unique storage key for an asset.

        Args:
            filename: Original filename
            prefix: Optional path prefix (e.g., 'characters', 'animations')

        Returns:
            str: Unique storage key
        """
        # Generate unique identifier
        unique_id = uuid.uuid4().hex[:12]
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")

        # Extract extension
        ext = ""
        if "." in filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower()

        # Build key path
        if prefix:
            return f"{prefix}/{timestamp}/{unique_id}{ext}"
        return f"{timestamp}/{unique_id}{ext}"

    async def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        prefix: str = "",
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload a file to storage.

        Args:
            file_bytes: File content as bytes
            filename: Original filename
            content_type: MIME type of the file
            prefix: Optional path prefix for organization
            metadata: Optional metadata to store with the file

        Returns:
            str: Public URL of the uploaded file

        Raises:
            UploadError: If upload fails
        """
        # Validate file size
        file_size = len(file_bytes)
        if file_size > self.settings.max_upload_size_bytes:
            raise UploadError(
                f"File size ({file_size} bytes) exceeds maximum allowed "
                f"({self.settings.max_upload_size_bytes} bytes)"
            )

        # Generate unique key
        key = self._generate_asset_key(filename, prefix)

        # Prepare extra args
        extra_args = {
            "ContentType": content_type,
            "ACL": "public-read",  # Make files publicly readable
        }

        if metadata:
            extra_args["Metadata"] = {k: str(v) for k, v in metadata.items()}

        try:
            # Upload file
            self.client.upload_fileobj(
                io.BytesIO(file_bytes),
                self.settings.storage_bucket_name,
                key,
                ExtraArgs=extra_args
            )

            logger.info(f"Successfully uploaded file: {key}")

            # Return public URL
            return f"{self.settings.public_url_base}/{key}"

        except ClientError as e:
            logger.error(f"Failed to upload file {filename}: {e}")
            raise UploadError(f"Failed to upload file: {e}")

    async def get_signed_url(
        self,
        asset_id: str,
        expires_in: int = 3600,
        method: str = "get_object"
    ) -> str:
        """
        Generate a signed URL for accessing an asset.

        Args:
            asset_id: The storage key or asset identifier
            expires_in: URL expiration time in seconds (default: 1 hour)
            method: S3 operation ('get_object' for download, 'put_object' for upload)

        Returns:
            str: Signed URL for accessing the asset
        """
        try:
            params = {
                "Bucket": self.settings.storage_bucket_name,
                "Key": asset_id,
            }

            url = self.client.generate_presigned_url(
                ClientMethod=method,
                Params=params,
                ExpiresIn=expires_in
            )

            logger.debug(f"Generated signed URL for {asset_id}, expires in {expires_in}s")
            return url

        except ClientError as e:
            logger.error(f"Failed to generate signed URL for {asset_id}: {e}")
            raise StorageError(f"Failed to generate signed URL: {e}")

    async def generate_upload_url(
        self,
        filename: str,
        content_type: str,
        prefix: str = "",
        expires_in: Optional[int] = None
    ) -> dict:
        """
        Generate a presigned URL for direct client upload.

        Args:
            filename: Original filename
            content_type: MIME type of the file
            prefix: Optional path prefix
            expires_in: URL expiration time in seconds

        Returns:
            dict: Contains 'upload_url', 'key', and 'public_url'
        """
        if expires_in is None:
            expires_in = self.settings.upload_url_expiration

        # Generate key
        key = self._generate_asset_key(filename, prefix)

        try:
            # Generate presigned POST URL
            presigned_post = self.client.generate_presigned_post(
                Bucket=self.settings.storage_bucket_name,
                Key=key,
                Fields={
                    "Content-Type": content_type,
                    "acl": "public-read",
                },
                Conditions=[
                    {"Content-Type": content_type},
                    {"acl": "public-read"},
                    ["content-length-range", 1, self.settings.max_upload_size_bytes],
                ],
                ExpiresIn=expires_in
            )

            public_url = f"{self.settings.public_url_base}/{key}"

            logger.info(f"Generated upload URL for key: {key}")

            return {
                "upload_url": presigned_post["url"],
                "fields": presigned_post["fields"],
                "key": key,
                "public_url": public_url,
                "expires_in": expires_in
            }

        except ClientError as e:
            logger.error(f"Failed to generate upload URL: {e}")
            raise StorageError(f"Failed to generate upload URL: {e}")

    async def delete_asset(self, asset_id: str) -> None:
        """
        Delete an asset from storage.

        Args:
            asset_id: The storage key of the asset to delete

        Raises:
            StorageError: If deletion fails
        """
        try:
            self.client.delete_object(
                Bucket=self.settings.storage_bucket_name,
                Key=asset_id
            )
            logger.info(f"Successfully deleted asset: {asset_id}")

        except ClientError as e:
            logger.error(f"Failed to delete asset {asset_id}: {e}")
            raise StorageError(f"Failed to delete asset: {e}")

    async def delete_assets_batch(self, asset_ids: list[str]) -> dict:
        """
        Delete multiple assets from storage.

        Args:
            asset_ids: List of storage keys to delete

        Returns:
            dict: Contains 'deleted' and 'errors' lists
        """
        if not asset_ids:
            return {"deleted": [], "errors": []}

        # S3 batch delete supports up to 1000 objects
        objects = [{"Key": key} for key in asset_ids[:1000]]

        try:
            response = self.client.delete_objects(
                Bucket=self.settings.storage_bucket_name,
                Delete={"Objects": objects}
            )

            deleted = [obj["Key"] for obj in response.get("Deleted", [])]
            errors = [
                {"key": err["Key"], "error": err["Message"]}
                for err in response.get("Errors", [])
            ]

            logger.info(f"Batch delete: {len(deleted)} deleted, {len(errors)} errors")

            return {"deleted": deleted, "errors": errors}

        except ClientError as e:
            logger.error(f"Failed to batch delete assets: {e}")
            raise StorageError(f"Failed to batch delete assets: {e}")

    async def get_asset_info(self, asset_id: str) -> dict:
        """
        Get metadata about an asset.

        Args:
            asset_id: The storage key of the asset

        Returns:
            dict: Asset metadata including size, content_type, last_modified
        """
        try:
            response = self.client.head_object(
                Bucket=self.settings.storage_bucket_name,
                Key=asset_id
            )

            return {
                "key": asset_id,
                "size": response["ContentLength"],
                "content_type": response.get("ContentType", "application/octet-stream"),
                "last_modified": response["LastModified"].isoformat(),
                "metadata": response.get("Metadata", {}),
                "public_url": f"{self.settings.public_url_base}/{asset_id}"
            }

        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(f"Asset not found: {asset_id}")
            logger.error(f"Failed to get asset info for {asset_id}: {e}")
            raise StorageError(f"Failed to get asset info: {e}")

    async def create_zip_download(
        self,
        asset_ids: list[str],
        zip_filename: str = "assets.zip"
    ) -> str:
        """
        Create a ZIP file containing multiple assets and return download URL.

        Args:
            asset_ids: List of storage keys to include in ZIP
            zip_filename: Name for the ZIP file

        Returns:
            str: Signed URL for downloading the ZIP file
        """
        if not asset_ids:
            raise StorageError("No assets provided for ZIP creation")

        # Create ZIP in memory
        zip_buffer = io.BytesIO()

        try:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for asset_id in asset_ids:
                    try:
                        # Download file content
                        response = self.client.get_object(
                            Bucket=self.settings.storage_bucket_name,
                            Key=asset_id
                        )
                        file_content = response["Body"].read()

                        # Extract filename from key
                        filename = asset_id.rsplit("/", 1)[-1]

                        # Add to ZIP
                        zip_file.writestr(filename, file_content)

                    except ClientError as e:
                        logger.warning(f"Failed to include {asset_id} in ZIP: {e}")
                        continue

            # Reset buffer position
            zip_buffer.seek(0)
            zip_content = zip_buffer.read()

            # Upload ZIP to temp location
            zip_key = self._generate_asset_key(zip_filename, self.settings.temp_path)

            self.client.upload_fileobj(
                io.BytesIO(zip_content),
                self.settings.storage_bucket_name,
                zip_key,
                ExtraArgs={
                    "ContentType": "application/zip",
                    "ContentDisposition": f'attachment; filename="{zip_filename}"'
                }
            )

            # Generate signed download URL (1 hour expiration)
            download_url = await self.get_signed_url(zip_key, expires_in=3600)

            logger.info(f"Created ZIP with {len(asset_ids)} assets: {zip_key}")

            return download_url

        except Exception as e:
            logger.error(f"Failed to create ZIP download: {e}")
            raise StorageError(f"Failed to create ZIP download: {e}")

    async def list_assets(
        self,
        prefix: str = "",
        max_keys: int = 1000,
        continuation_token: Optional[str] = None
    ) -> dict:
        """
        List assets in storage.

        Args:
            prefix: Filter by path prefix
            max_keys: Maximum number of results
            continuation_token: Token for pagination

        Returns:
            dict: Contains 'assets' list and optional 'next_token'
        """
        params = {
            "Bucket": self.settings.storage_bucket_name,
            "MaxKeys": max_keys,
        }

        if prefix:
            params["Prefix"] = prefix

        if continuation_token:
            params["ContinuationToken"] = continuation_token

        try:
            response = self.client.list_objects_v2(**params)

            assets = [
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                    "public_url": f"{self.settings.public_url_base}/{obj['Key']}"
                }
                for obj in response.get("Contents", [])
            ]

            result = {"assets": assets}

            if response.get("IsTruncated"):
                result["next_token"] = response.get("NextContinuationToken")

            return result

        except ClientError as e:
            logger.error(f"Failed to list assets: {e}")
            raise StorageError(f"Failed to list assets: {e}")

    async def copy_asset(self, source_key: str, dest_key: str) -> str:
        """
        Copy an asset within storage.

        Args:
            source_key: Source asset key
            dest_key: Destination asset key

        Returns:
            str: Public URL of the copied asset
        """
        try:
            self.client.copy_object(
                Bucket=self.settings.storage_bucket_name,
                CopySource={
                    "Bucket": self.settings.storage_bucket_name,
                    "Key": source_key
                },
                Key=dest_key,
                ACL="public-read"
            )

            logger.info(f"Copied asset from {source_key} to {dest_key}")
            return f"{self.settings.public_url_base}/{dest_key}"

        except ClientError as e:
            logger.error(f"Failed to copy asset: {e}")
            raise StorageError(f"Failed to copy asset: {e}")


# Module-level convenience functions for interface contract compliance
_storage_service: Optional[StorageService | LocalStorageService] = None


def get_storage_service() -> StorageService | LocalStorageService:
    """Get or create storage service instance based on storage mode."""
    global _storage_service
    if _storage_service is None:
        settings = get_storage_settings()
        if settings.storage_mode == "local":
            logger.info("Using local storage for development")
            _storage_service = LocalStorageService()
        else:
            logger.info("Using S3-compatible storage")
            _storage_service = StorageService()
    return _storage_service


async def upload_file(
    file_bytes: bytes,
    filename: str,
    content_type: str,
    prefix: str = ""
) -> str:
    """
    Upload a file to storage.

    Args:
        file_bytes: File content as bytes
        filename: Original filename
        content_type: MIME type of the file
        prefix: Optional path prefix

    Returns:
        str: Public URL of the uploaded file
    """
    service = get_storage_service()
    return await service.upload_file(file_bytes, filename, content_type, prefix)


async def get_signed_url(asset_id: str, expires_in: int = 3600) -> str:
    """
    Generate a signed URL for accessing an asset.

    Args:
        asset_id: The storage key or asset identifier
        expires_in: URL expiration time in seconds

    Returns:
        str: Signed URL for accessing the asset
    """
    service = get_storage_service()
    return await service.get_signed_url(asset_id, expires_in)


async def delete_asset(asset_id: str) -> None:
    """
    Delete an asset from storage.

    Args:
        asset_id: The storage key of the asset to delete
    """
    service = get_storage_service()
    await service.delete_asset(asset_id)


async def create_zip_download(asset_ids: list[str]) -> str:
    """
    Create a ZIP file containing multiple assets and return download URL.

    Args:
        asset_ids: List of storage keys to include in ZIP

    Returns:
        str: Signed URL for downloading the ZIP file
    """
    service = get_storage_service()
    return await service.create_zip_download(asset_ids)
