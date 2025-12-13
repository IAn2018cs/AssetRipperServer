"""Health check endpoint."""

import logging
import time

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.assetripper import assetripper_manager
from app.core.task_queue import task_queue_manager
from app.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Track startup time for uptime calculation
_startup_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> JSONResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse: Health status information
    """
    # Check AssetRipper status
    is_healthy = await assetripper_manager.is_healthy()
    assetripper_status = "running" if is_healthy else "down"

    # Get queue information
    queue_size = task_queue_manager.get_queue_size()
    current_task = task_queue_manager.get_current_task_id()

    # Calculate uptime
    uptime_seconds = int(time.time() - _startup_time)

    # Determine overall status
    overall_status = "healthy" if is_healthy else "unhealthy"
    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    response_data = HealthResponse(
        status=overall_status,
        assetripper_status=assetripper_status,
        queue_size=queue_size,
        current_task=current_task,
        uptime_seconds=uptime_seconds,
    )

    return JSONResponse(
        status_code=status_code,
        content=response_data.model_dump(),
    )
