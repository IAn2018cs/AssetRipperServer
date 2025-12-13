"""Database models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Task(Base):
    """Task model for tracking AssetRipper processing tasks."""

    __tablename__ = "tasks"

    # Primary key
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # File information
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    upload_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )

    # Export information
    export_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    export_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Error tracking
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # Metadata
    user_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)

    # Indexes
    __table_args__ = (
        Index("idx_status", "status"),
        Index("idx_created_at", "created_at"),
        Index("idx_file_hash", "file_hash"),
    )

    def __repr__(self) -> str:
        """String representation of Task."""
        return f"<Task(id={self.id}, status={self.status}, filename={self.original_filename})>"


class CleanupLog(Base):
    """Log of file cleanup operations."""

    __tablename__ = "cleanup_log"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Cleanup info
    cleaned_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    task_id: Mapped[str] = mapped_column(String(36), nullable=False)
    upload_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    export_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    reason: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'retention_expired', 'manual', 'failed'

    def __repr__(self) -> str:
        """String representation of CleanupLog."""
        return f"<CleanupLog(id={self.id}, task_id={self.task_id}, reason={self.reason})>"
