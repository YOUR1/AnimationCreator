"""
Asset cleanup service for managing orphaned and old files.

This module provides utilities for:
- Identifying orphaned files (files in storage but not in database)
- Deleting old/unused assets based on retention policies
- Configurable cleanup schedules
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Callable, Any

from app.core.storage_config import get_storage_settings
from app.services.storage import get_storage_service, StorageError

logger = logging.getLogger(__name__)


class CleanupConfig:
    """Configuration for asset cleanup policies."""

    def __init__(
        self,
        # Temp files (ZIP downloads, etc.)
        temp_retention_hours: int = 24,

        # Orphaned files (not referenced in database)
        orphan_grace_period_hours: int = 48,

        # Deleted user assets (soft-deleted)
        deleted_retention_days: int = 30,

        # Unused character assets (no generation in X days)
        unused_retention_days: int = 90,

        # Batch size for cleanup operations
        batch_size: int = 100,

        # Dry run mode (log actions without executing)
        dry_run: bool = False
    ):
        self.temp_retention_hours = temp_retention_hours
        self.orphan_grace_period_hours = orphan_grace_period_hours
        self.deleted_retention_days = deleted_retention_days
        self.unused_retention_days = unused_retention_days
        self.batch_size = batch_size
        self.dry_run = dry_run


class CleanupService:
    """
    Service for cleaning up orphaned and old assets.

    Provides methods to identify and remove files that are no longer needed.
    """

    def __init__(self, config: Optional[CleanupConfig] = None):
        self.config = config or CleanupConfig()
        self.storage = get_storage_service()
        self.settings = get_storage_settings()

    async def cleanup_temp_files(self) -> dict:
        """
        Remove temporary files older than retention period.

        Temp files include:
        - ZIP downloads
        - Processing intermediates

        Returns:
            dict: Cleanup results with deleted count and errors
        """
        logger.info(f"Starting temp file cleanup (retention: {self.config.temp_retention_hours}h)")

        cutoff_time = datetime.utcnow() - timedelta(hours=self.config.temp_retention_hours)
        deleted = []
        errors = []

        try:
            # List files in temp directory
            result = await self.storage.list_assets(
                prefix=self.settings.temp_path,
                max_keys=self.config.batch_size
            )

            for asset in result.get("assets", []):
                # Parse last modified time
                last_modified = datetime.fromisoformat(
                    asset["last_modified"].replace("Z", "+00:00")
                ).replace(tzinfo=None)

                if last_modified < cutoff_time:
                    if self.config.dry_run:
                        logger.info(f"[DRY RUN] Would delete temp file: {asset['key']}")
                        deleted.append(asset["key"])
                    else:
                        try:
                            await self.storage.delete_asset(asset["key"])
                            deleted.append(asset["key"])
                            logger.debug(f"Deleted temp file: {asset['key']}")
                        except StorageError as e:
                            errors.append({"key": asset["key"], "error": str(e)})
                            logger.error(f"Failed to delete temp file {asset['key']}: {e}")

            logger.info(f"Temp cleanup complete: {len(deleted)} deleted, {len(errors)} errors")

        except Exception as e:
            logger.error(f"Temp cleanup failed: {e}")
            errors.append({"error": str(e)})

        return {
            "deleted_count": len(deleted),
            "deleted_keys": deleted,
            "errors": errors,
            "dry_run": self.config.dry_run
        }

    async def find_orphaned_files(
        self,
        db_asset_keys: set[str],
        prefix: str = ""
    ) -> list[dict]:
        """
        Find files in storage that are not referenced in the database.

        Args:
            db_asset_keys: Set of asset keys from the database
            prefix: Optional prefix to limit search scope

        Returns:
            List of orphaned asset info dicts
        """
        logger.info("Searching for orphaned files")

        orphaned = []
        continuation_token = None

        try:
            while True:
                result = await self.storage.list_assets(
                    prefix=prefix,
                    max_keys=1000,
                    continuation_token=continuation_token
                )

                for asset in result.get("assets", []):
                    key = asset["key"]

                    # Skip temp directory (handled separately)
                    if key.startswith(self.settings.temp_path):
                        continue

                    # Check if asset exists in database
                    if key not in db_asset_keys:
                        # Check grace period
                        last_modified = datetime.fromisoformat(
                            asset["last_modified"].replace("Z", "+00:00")
                        ).replace(tzinfo=None)

                        grace_cutoff = datetime.utcnow() - timedelta(
                            hours=self.config.orphan_grace_period_hours
                        )

                        if last_modified < grace_cutoff:
                            orphaned.append({
                                "key": key,
                                "size": asset["size"],
                                "last_modified": asset["last_modified"]
                            })

                # Check for more results
                continuation_token = result.get("next_token")
                if not continuation_token:
                    break

            logger.info(f"Found {len(orphaned)} orphaned files")

        except Exception as e:
            logger.error(f"Failed to search for orphaned files: {e}")
            raise

        return orphaned

    async def cleanup_orphaned_files(
        self,
        db_asset_keys: set[str],
        prefix: str = ""
    ) -> dict:
        """
        Remove orphaned files from storage.

        Args:
            db_asset_keys: Set of asset keys from the database
            prefix: Optional prefix to limit search scope

        Returns:
            dict: Cleanup results
        """
        logger.info("Starting orphaned file cleanup")

        orphaned = await self.find_orphaned_files(db_asset_keys, prefix)

        if not orphaned:
            return {
                "deleted_count": 0,
                "deleted_keys": [],
                "errors": [],
                "dry_run": self.config.dry_run
            }

        deleted = []
        errors = []

        # Process in batches
        for i in range(0, len(orphaned), self.config.batch_size):
            batch = orphaned[i:i + self.config.batch_size]
            batch_keys = [asset["key"] for asset in batch]

            if self.config.dry_run:
                logger.info(f"[DRY RUN] Would delete {len(batch_keys)} orphaned files")
                deleted.extend(batch_keys)
            else:
                try:
                    result = await self.storage.delete_assets_batch(batch_keys)
                    deleted.extend(result.get("deleted", []))
                    errors.extend(result.get("errors", []))
                except StorageError as e:
                    logger.error(f"Batch delete failed: {e}")
                    errors.append({"error": str(e)})

        logger.info(f"Orphaned cleanup complete: {len(deleted)} deleted, {len(errors)} errors")

        return {
            "deleted_count": len(deleted),
            "deleted_keys": deleted,
            "errors": errors,
            "dry_run": self.config.dry_run
        }

    async def cleanup_deleted_user_assets(
        self,
        get_deleted_user_ids: Callable[[], list[str]]
    ) -> dict:
        """
        Remove assets belonging to deleted users.

        Args:
            get_deleted_user_ids: Callback to get user IDs that were deleted
                                  more than retention_days ago

        Returns:
            dict: Cleanup results
        """
        logger.info(
            f"Starting deleted user asset cleanup "
            f"(retention: {self.config.deleted_retention_days} days)"
        )

        deleted_user_ids = get_deleted_user_ids()

        if not deleted_user_ids:
            return {
                "deleted_count": 0,
                "deleted_keys": [],
                "users_processed": 0,
                "errors": [],
                "dry_run": self.config.dry_run
            }

        deleted = []
        errors = []

        for user_id in deleted_user_ids:
            # Search for assets with user ID prefix pattern
            # Assumes assets are organized as: {type}/{date}/{user_id}_{asset_id}
            # or there's metadata tagging

            try:
                # This would need to be adapted based on actual storage organization
                # For now, using character/animation prefixes
                for prefix in [self.settings.characters_path, self.settings.animations_path]:
                    result = await self.storage.list_assets(prefix=prefix)

                    for asset in result.get("assets", []):
                        # Check if asset belongs to deleted user
                        # This check depends on naming convention or metadata
                        if user_id in asset["key"]:
                            if self.config.dry_run:
                                logger.info(
                                    f"[DRY RUN] Would delete user asset: {asset['key']}"
                                )
                                deleted.append(asset["key"])
                            else:
                                try:
                                    await self.storage.delete_asset(asset["key"])
                                    deleted.append(asset["key"])
                                except StorageError as e:
                                    errors.append({"key": asset["key"], "error": str(e)})

            except Exception as e:
                logger.error(f"Failed to cleanup assets for user {user_id}: {e}")
                errors.append({"user_id": user_id, "error": str(e)})

        logger.info(
            f"Deleted user cleanup complete: {len(deleted)} assets deleted, "
            f"{len(deleted_user_ids)} users processed"
        )

        return {
            "deleted_count": len(deleted),
            "deleted_keys": deleted,
            "users_processed": len(deleted_user_ids),
            "errors": errors,
            "dry_run": self.config.dry_run
        }

    async def get_storage_stats(self) -> dict:
        """
        Get storage usage statistics.

        Returns:
            dict: Storage statistics by category
        """
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "by_category": {}
        }

        categories = {
            "characters": self.settings.characters_path,
            "animations": self.settings.animations_path,
            "thumbnails": self.settings.thumbnails_path,
            "temp": self.settings.temp_path,
        }

        for category, prefix in categories.items():
            try:
                result = await self.storage.list_assets(prefix=prefix, max_keys=10000)
                assets = result.get("assets", [])

                category_size = sum(a["size"] for a in assets)
                category_count = len(assets)

                stats["by_category"][category] = {
                    "file_count": category_count,
                    "size_bytes": category_size,
                    "size_mb": round(category_size / (1024 * 1024), 2)
                }

                stats["total_files"] += category_count
                stats["total_size_bytes"] += category_size

            except Exception as e:
                logger.error(f"Failed to get stats for {category}: {e}")
                stats["by_category"][category] = {"error": str(e)}

        stats["total_size_mb"] = round(stats["total_size_bytes"] / (1024 * 1024), 2)
        stats["total_size_gb"] = round(stats["total_size_bytes"] / (1024 * 1024 * 1024), 2)

        return stats

    async def run_full_cleanup(
        self,
        db_asset_keys: Optional[set[str]] = None,
        get_deleted_user_ids: Optional[Callable[[], list[str]]] = None
    ) -> dict:
        """
        Run all cleanup tasks.

        Args:
            db_asset_keys: Set of asset keys from database (for orphan detection)
            get_deleted_user_ids: Callback to get deleted user IDs

        Returns:
            dict: Combined cleanup results
        """
        logger.info("Starting full cleanup run")

        results = {
            "started_at": datetime.utcnow().isoformat(),
            "temp_cleanup": None,
            "orphan_cleanup": None,
            "deleted_user_cleanup": None,
            "completed_at": None,
            "dry_run": self.config.dry_run
        }

        # Cleanup temp files
        results["temp_cleanup"] = await self.cleanup_temp_files()

        # Cleanup orphaned files (if db keys provided)
        if db_asset_keys is not None:
            results["orphan_cleanup"] = await self.cleanup_orphaned_files(db_asset_keys)

        # Cleanup deleted user assets (if callback provided)
        if get_deleted_user_ids is not None:
            results["deleted_user_cleanup"] = await self.cleanup_deleted_user_assets(
                get_deleted_user_ids
            )

        results["completed_at"] = datetime.utcnow().isoformat()

        # Calculate totals
        total_deleted = 0
        total_errors = 0

        for key in ["temp_cleanup", "orphan_cleanup", "deleted_user_cleanup"]:
            if results[key]:
                total_deleted += results[key].get("deleted_count", 0)
                total_errors += len(results[key].get("errors", []))

        results["summary"] = {
            "total_deleted": total_deleted,
            "total_errors": total_errors
        }

        logger.info(
            f"Full cleanup complete: {total_deleted} files deleted, "
            f"{total_errors} errors"
        )

        return results


# Module-level convenience functions
_cleanup_service: Optional[CleanupService] = None


def get_cleanup_service(config: Optional[CleanupConfig] = None) -> CleanupService:
    """Get or create cleanup service instance."""
    global _cleanup_service
    if _cleanup_service is None or config is not None:
        _cleanup_service = CleanupService(config)
    return _cleanup_service


async def cleanup_temp_files() -> dict:
    """Convenience function to cleanup temp files."""
    service = get_cleanup_service()
    return await service.cleanup_temp_files()


async def find_orphaned_files(db_asset_keys: set[str]) -> list[dict]:
    """Convenience function to find orphaned files."""
    service = get_cleanup_service()
    return await service.find_orphaned_files(db_asset_keys)


async def run_scheduled_cleanup(
    db_asset_keys: Optional[set[str]] = None,
    get_deleted_user_ids: Optional[Callable[[], list[str]]] = None
) -> dict:
    """
    Run scheduled cleanup tasks.

    This function is intended to be called by a scheduler (e.g., Celery beat).
    """
    service = get_cleanup_service()
    return await service.run_full_cleanup(db_asset_keys, get_deleted_user_ids)
