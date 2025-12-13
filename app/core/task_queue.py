"""Task queue processor."""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.assetripper import AssetRipperError, assetripper_manager
from app.database import AsyncSessionLocal
from app.models import Task
from app.schemas import TaskStatus
from app.utils.file_utils import (
    create_zip_archive,
    get_directory_size,
    get_task_assets_dir,
    get_task_export_dir,
    get_task_upload_path,
)

logger = logging.getLogger(__name__)


class TaskQueueManager:
    """
    Manager for task queue processing.

    Handles sequential processing of tasks using a single AssetRipper instance.
    """

    def __init__(self):
        """Initialize task queue manager."""
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.current_task_id: Optional[str] = None
        self._running = False

    async def start(self) -> None:
        """Start the task queue worker."""
        if self._running:
            logger.warning("Task queue worker already running")
            return

        self._running = True
        self.worker_task = asyncio.create_task(self._worker())
        logger.info("Task queue worker started")

        # Recover interrupted tasks from previous run
        await self._recover_interrupted_tasks()

    async def stop(self) -> None:
        """Stop the task queue worker."""
        if not self._running:
            return

        self._running = False

        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        logger.info("Task queue worker stopped")

    async def add_task(self, task_id: str) -> None:
        """
        Add a task to the queue.

        Args:
            task_id: Task ID to process
        """
        await self.queue.put(task_id)
        logger.info(f"Task {task_id} added to queue (queue size: {self.queue.qsize()})")

    def get_queue_size(self) -> int:
        """
        Get current queue size.

        Returns:
            int: Number of tasks in queue
        """
        return self.queue.qsize()

    def get_current_task_id(self) -> Optional[str]:
        """
        Get currently processing task ID.

        Returns:
            Optional[str]: Current task ID or None
        """
        return self.current_task_id

    async def _worker(self) -> None:
        """Background worker coroutine that processes tasks sequentially."""
        logger.info("Task queue worker loop started")

        while self._running:
            try:
                # Get next task from queue (with timeout to allow checking _running)
                try:
                    task_id = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                self.current_task_id = task_id
                logger.info(f"Processing task {task_id}")

                # Process the task
                try:
                    await self._process_task(task_id)
                except Exception as e:
                    logger.exception(f"Error processing task {task_id}: {e}")
                    await self._mark_task_failed(task_id, str(e))
                finally:
                    self.current_task_id = None
                    self.queue.task_done()

            except asyncio.CancelledError:
                logger.info("Task queue worker cancelled")
                break
            except Exception as e:
                logger.exception(f"Unexpected error in worker loop: {e}")
                await asyncio.sleep(1)  # Avoid tight loop on persistent errors

        logger.info("Task queue worker loop ended")

    async def _process_task(self, task_id: str) -> None:
        """
        Process a single task.

        Args:
            task_id: Task ID to process
        """
        async with AsyncSessionLocal() as db:
            # Get task from database
            result = await db.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()

            if not task:
                logger.error(f"Task {task_id} not found in database")
                return

            if task.status != TaskStatus.PENDING:
                logger.warning(f"Task {task_id} is not PENDING (status: {task.status}), skipping")
                return

            # Update status to PROCESSING
            task.status = TaskStatus.PROCESSING
            task.started_at = datetime.utcnow()
            await db.commit()

            logger.info(f"Task {task_id} started processing")

        try:
            # Step 1: Load file into AssetRipper
            upload_path = Path(task.upload_path)
            if not upload_path.exists():
                raise FileNotFoundError(f"Upload file not found: {upload_path}")

            logger.info(f"Task {task_id}: Loading file into AssetRipper: {upload_path}")
            await assetripper_manager.load_file(str(upload_path.absolute()))

            # Step 2: Export primary content
            export_dir = get_task_export_dir(task_id)
            logger.info(f"Task {task_id}: Exporting to: {export_dir}")
            await assetripper_manager.export_primary_content(str(export_dir.absolute()))

            # Step 3: Verify Assets directory exists
            assets_dir = get_task_assets_dir(task_id)
            if not assets_dir.exists():
                raise FileNotFoundError(f"Assets directory not found after export: {assets_dir}")

            # Step 4: Calculate export size
            export_size = get_directory_size(assets_dir)
            logger.info(f"Task {task_id}: Export size: {export_size} bytes")

            # Step 5: Create ZIP archive of Assets directory
            # Note: We don't create ZIP here, we'll do it on-demand when downloading
            # to save disk space

            # Step 6: Reset AssetRipper for next task
            try:
                await assetripper_manager.reset()
            except Exception as e:
                logger.warning(f"Failed to reset AssetRipper after task {task_id}: {e}")

            # Update task as completed
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Task)
                    .where(Task.id == task_id)
                    .values(
                        status=TaskStatus.COMPLETED,
                        completed_at=datetime.utcnow(),
                        export_path=str(assets_dir),
                        export_size_bytes=export_size,
                        error_message=None,
                    )
                )
                await db.commit()

            logger.info(f"Task {task_id} completed successfully")

        except AssetRipperError as e:
            logger.error(f"Task {task_id} failed due to AssetRipper error: {e}")
            await self._mark_task_failed(task_id, f"AssetRipper error: {e}")

            # Try to reset AssetRipper
            try:
                await assetripper_manager.reset()
            except Exception as reset_error:
                logger.error(f"Failed to reset AssetRipper: {reset_error}")

        except Exception as e:
            logger.exception(f"Task {task_id} failed with unexpected error: {e}")
            await self._mark_task_failed(task_id, f"Unexpected error: {e}")

    async def _mark_task_failed(self, task_id: str, error_message: str) -> None:
        """
        Mark a task as failed.

        Args:
            task_id: Task ID
            error_message: Error message
        """
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(Task)
                .where(Task.id == task_id)
                .values(
                    status=TaskStatus.FAILED,
                    completed_at=datetime.utcnow(),
                    error_message=error_message,
                )
            )
            await db.commit()

        logger.info(f"Task {task_id} marked as FAILED")

    async def _recover_interrupted_tasks(self) -> None:
        """
        Recover tasks that were interrupted by container restart.

        Marks all PROCESSING tasks as FAILED.
        """
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Task).where(Task.status == TaskStatus.PROCESSING)
            )
            interrupted_tasks = result.scalars().all()

            if interrupted_tasks:
                logger.info(f"Found {len(interrupted_tasks)} interrupted tasks, marking as FAILED")

                for task in interrupted_tasks:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.utcnow()
                    task.error_message = "Interrupted by container restart"

                await db.commit()
                logger.info(f"Marked {len(interrupted_tasks)} interrupted tasks as FAILED")


# Global task queue manager instance
task_queue_manager = TaskQueueManager()
