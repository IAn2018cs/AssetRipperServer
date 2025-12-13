"""File operation utilities."""

import hashlib
import logging
import shutil
import zipfile
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import UploadFile

from app.config import settings

logger = logging.getLogger(__name__)


async def save_upload_file(upload_file: UploadFile, destination: Path) -> int:
    """
    Save uploaded file to destination using streaming to avoid memory issues.

    Args:
        upload_file: FastAPI UploadFile object
        destination: Destination file path

    Returns:
        int: File size in bytes
    """
    destination.parent.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    async with aiofiles.open(destination, "wb") as f:
        while chunk := await upload_file.read(8192):  # 8KB chunks
            await f.write(chunk)
            total_bytes += len(chunk)

    logger.info(f"Saved upload file to {destination} ({total_bytes} bytes)")
    return total_bytes


async def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA256 hash of a file.

    Args:
        file_path: Path to file

    Returns:
        str: Hex string of SHA256 hash
    """
    sha256 = hashlib.sha256()

    async with aiofiles.open(file_path, "rb") as f:
        while chunk := await f.read(8192):
            sha256.update(chunk)

    return sha256.hexdigest()


def get_directory_size(directory: Path) -> int:
    """
    Calculate total size of directory recursively.

    Args:
        directory: Directory path

    Returns:
        int: Total size in bytes
    """
    total_size = 0

    for item in directory.rglob("*"):
        if item.is_file():
            total_size += item.stat().st_size

    return total_size


def create_zip_archive(source_dir: Path, output_zip: Path, arcname: Optional[str] = None) -> int:
    """
    Create a zip archive from a directory.

    Args:
        source_dir: Source directory to archive
        output_zip: Output zip file path
        arcname: Archive name (defaults to source_dir name)

    Returns:
        int: Zip file size in bytes
    """
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    output_zip.parent.mkdir(parents=True, exist_ok=True)

    arcname = arcname or source_dir.name

    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                # Calculate relative path for archive
                rel_path = file_path.relative_to(source_dir)
                arc_path = Path(arcname) / rel_path
                zipf.write(file_path, arc_path)

    zip_size = output_zip.stat().st_size
    logger.info(f"Created zip archive: {output_zip} ({zip_size} bytes)")
    return zip_size


def delete_directory(directory: Path) -> None:
    """
    Delete a directory and all its contents.

    Args:
        directory: Directory to delete
    """
    if directory.exists():
        shutil.rmtree(directory)
        logger.info(f"Deleted directory: {directory}")


def delete_file(file_path: Path) -> None:
    """
    Delete a file.

    Args:
        file_path: File to delete
    """
    if file_path.exists():
        file_path.unlink()
        logger.info(f"Deleted file: {file_path}")


def ensure_task_directories(task_id: str) -> tuple[Path, Path]:
    """
    Ensure upload and export directories exist for a task.

    Args:
        task_id: Task ID

    Returns:
        tuple: (upload_dir, export_dir)
    """
    upload_dir = settings.upload_dir / task_id
    export_dir = settings.export_dir / task_id

    upload_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)

    return upload_dir, export_dir


def get_task_upload_path(task_id: str, filename: str) -> Path:
    """
    Get upload file path for a task.

    Args:
        task_id: Task ID
        filename: Original filename

    Returns:
        Path: Upload file path
    """
    upload_dir = settings.upload_dir / task_id
    return upload_dir / filename


def get_task_export_dir(task_id: str) -> Path:
    """
    Get export directory path for a task.

    Args:
        task_id: Task ID

    Returns:
        Path: Export directory path
    """
    return settings.export_dir / task_id


def get_task_assets_dir(task_id: str) -> Path:
    """
    Get Assets directory path for a task (inside export directory).

    Args:
        task_id: Task ID

    Returns:
        Path: Assets directory path
    """
    return get_task_export_dir(task_id) / "Assets"


def cleanup_task_files(task_id: str) -> None:
    """
    Clean up all files for a task (upload and export).

    Args:
        task_id: Task ID
    """
    upload_dir = settings.upload_dir / task_id
    export_dir = settings.export_dir / task_id

    delete_directory(upload_dir)
    delete_directory(export_dir)

    logger.info(f"Cleaned up files for task {task_id}")
