"""Pydantic schemas for API request and response models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskStatus:
    """Task status constants."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    original_filename: str
    upload_path: str
    file_size_bytes: int
    file_hash: Optional[str] = None
    user_ip: Optional[str] = None


class TaskResponse(BaseModel):
    """Schema for task response."""

    task_id: str = Field(alias="id")
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    original_filename: str
    file_size_bytes: int
    export_path: Optional[str] = None
    export_size_bytes: Optional[int] = None
    error_message: Optional[str] = None

    class Config:
        """Pydantic config."""

        from_attributes = True
        populate_by_name = True


class TaskUploadResponse(BaseModel):
    """Schema for upload response."""

    task_id: str
    status: str
    message: str
    created_at: datetime


class HealthResponse(BaseModel):
    """Schema for health check response."""

    status: str
    assetripper_status: str
    queue_size: int
    current_task: Optional[str] = None
    uptime_seconds: Optional[int] = None


class ErrorResponse(BaseModel):
    """Schema for error response."""

    error: str
    detail: Optional[str] = None
    task_id: Optional[str] = None
