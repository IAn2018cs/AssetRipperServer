"""File cleanup scheduler."""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models import CleanupLog, Task
from app.utils.file_utils import cleanup_task_files

logger = logging.getLogger(__name__)


class FileCleanupScheduler:
    """
    Scheduler for automatic file cleanup.

    Runs periodic cleanup of old task files based on retention policy.
    """

    def __init__(self):
        """Initialize file cleanup scheduler."""
        self.scheduler = AsyncIOScheduler()
        self._running = False

    def start(self) -> None:
        """Start the cleanup scheduler."""
        if self._running:
            logger.warning("File cleanup scheduler already running")
            return

        # Parse cron expression
        cron_parts = settings.cleanup_schedule_cron.split()
        if len(cron_parts) != 5:
            logger.error(f"Invalid cron expression: {settings.cleanup_schedule_cron}")
            return

        minute, hour, day, month, day_of_week = cron_parts

        # Add cleanup job
        self.scheduler.add_job(
            self._cleanup_old_files,
            trigger="cron",
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            id="file_cleanup",
            name="Cleanup old task files",
            replace_existing=True,
        )

        self.scheduler.start()
        self._running = True

        logger.info(
            f"File cleanup scheduler started (schedule: {settings.cleanup_schedule_cron}, "
            f"retention: {settings.file_retention_days} days)"
        )

    def stop(self) -> None:
        """Stop the cleanup scheduler."""
        if not self._running:
            return

        self.scheduler.shutdown(wait=False)
        self._running = False
        logger.info("File cleanup scheduler stopped")

    async def _cleanup_old_files(self) -> None:
        """
        Clean up files for tasks older than retention period.

        This is the actual cleanup logic that runs on schedule.
        """
        logger.info("Starting scheduled file cleanup...")

        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=settings.file_retention_days)
        logger.info(f"Cleaning up tasks created before {cutoff_date}")

        async with AsyncSessionLocal() as db:
            # Find old tasks
            result = await db.execute(
                select(Task).where(Task.created_at < cutoff_date)
            )
            old_tasks = result.scalars().all()

            if not old_tasks:
                logger.info("No old tasks to clean up")
                return

            logger.info(f"Found {len(old_tasks)} tasks to clean up")

            cleaned_count = 0
            failed_count = 0

            for task in old_tasks:
                try:
                    # Clean up task files
                    cleanup_task_files(task.id)

                    # Log cleanup
                    cleanup_log = CleanupLog(
                        task_id=task.id,
                        upload_path=task.upload_path,
                        export_path=task.export_path,
                        reason="retention_expired",
                    )
                    db.add(cleanup_log)

                    # Optionally delete task record
                    # await db.delete(task)

                    cleaned_count += 1

                except Exception as e:
                    logger.error(f"Failed to clean up task {task.id}: {e}")
                    failed_count += 1

            # Commit cleanup logs
            await db.commit()

            logger.info(
                f"File cleanup completed: {cleaned_count} tasks cleaned, "
                f"{failed_count} failed"
            )


# Global file cleanup scheduler instance
file_cleanup_scheduler = FileCleanupScheduler()
