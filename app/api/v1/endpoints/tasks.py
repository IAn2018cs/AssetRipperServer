"""Task endpoints for querying and downloading."""

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Task
from app.schemas import TaskResponse, TaskStatus
from app.utils.file_utils import create_zip_archive, get_task_assets_dir

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskResponse:
    """
    Get task status and information.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        TaskResponse: Task information

    Raises:
        HTTPException: If task not found
    """
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return TaskResponse.model_validate(task)


@router.get("/download/{task_id}")
async def download_assets(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """
    Download exported Assets as a ZIP file.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        FileResponse: ZIP file containing Assets

    Raises:
        HTTPException: If task not found, not completed, or files missing
    """
    # Get task from database
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Check task status
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} is not completed (status: {task.status})",
        )

    # Check if Assets directory exists
    assets_dir = get_task_assets_dir(task_id)
    if not assets_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"Export files for task {task_id} have been cleaned up",
        )

    try:
        # Create ZIP file in temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
            tmp_zip_path = Path(tmp_file.name)

        # Create ZIP archive of Assets directory
        logger.info(f"Creating ZIP archive for task {task_id}")
        create_zip_archive(assets_dir, tmp_zip_path, arcname="Assets")

        # Return ZIP file
        return FileResponse(
            path=str(tmp_zip_path),
            media_type="application/zip",
            filename=f"{task.original_filename.rsplit('.', 1)[0]}_assets.zip",
            background=None,  # File will be deleted after response is sent
        )

    except Exception as e:
        logger.exception(f"Failed to create ZIP for task {task_id}: {e}")

        # Clean up temporary file if it exists
        if tmp_zip_path.exists():
            tmp_zip_path.unlink()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create download archive: {str(e)}",
        )


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete a task and its associated files.

    Args:
        task_id: Task ID
        db: Database session

    Returns:
        dict: Success message

    Raises:
        HTTPException: If task not found
    """
    from app.utils.file_utils import cleanup_task_files

    # Get task from database
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    # Clean up files
    try:
        cleanup_task_files(task_id)
    except Exception as e:
        logger.warning(f"Failed to clean up files for task {task_id}: {e}")

    # Delete task from database
    await db.delete(task)
    await db.commit()

    logger.info(f"Task {task_id} deleted")

    return {
        "message": f"Task {task_id} deleted successfully",
        "task_id": task_id,
    }
