"""Upload endpoint for file uploads."""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.task_queue import task_queue_manager
from app.database import get_db
from app.models import Task
from app.schemas import TaskStatus, TaskUploadResponse
from app.utils.file_utils import (
    calculate_file_hash,
    ensure_task_directories,
    get_task_upload_path,
    save_upload_file,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=TaskUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> TaskUploadResponse:
    """
    Upload a file (apk/xapk/ipa) for AssetRipper processing.

    Args:
        request: FastAPI request object
        file: Uploaded file
        db: Database session

    Returns:
        TaskUploadResponse: Task information

    Raises:
        HTTPException: If upload fails
    """
    logger.info(f"Received upload request for file: {file.filename}")

    # Validate file
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    # Generate task ID
    task_id = str(uuid.uuid4())

    try:
        # Ensure task directories exist
        upload_dir, export_dir = ensure_task_directories(task_id)

        # Save uploaded file
        upload_path = get_task_upload_path(task_id, file.filename)
        file_size = await save_upload_file(file, upload_path)

        # Calculate file hash (for potential deduplication)
        file_hash = await calculate_file_hash(upload_path)

        # Get client IP
        client_ip = request.client.host if request.client else None

        # Create task in database
        task = Task(
            id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow(),
            original_filename=file.filename,
            upload_path=str(upload_path),
            file_size_bytes=file_size,
            file_hash=file_hash,
            user_ip=client_ip,
        )

        db.add(task)
        await db.commit()

        logger.info(f"Task {task_id} created for file {file.filename} ({file_size} bytes)")

        # Add task to processing queue
        await task_queue_manager.add_task(task_id)

        return TaskUploadResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            message="File uploaded successfully. Task queued for processing.",
            created_at=task.created_at,
        )

    except Exception as e:
        logger.exception(f"Failed to upload file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )
