"""Application configuration management."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    environment: str = Field(default="development", description="Environment name")
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(default=None, description="Log file path")

    # AssetRipper settings
    assetripper_host: Optional[str] = Field(
        default=None, description="External AssetRipper host (e.g., http://localhost:8765). If set, will not start AssetRipper process"
    )
    assetripper_port: int = Field(default=8765, description="AssetRipper internal port")
    assetripper_binary_path: str = Field(
        default="/app/bin/AssetRipper.GUI.Free",
        description="Path to AssetRipper binary",
    )
    assetripper_startup_timeout: int = Field(
        default=30, description="AssetRipper startup timeout in seconds"
    )
    assetripper_health_check_interval: int = Field(
        default=30, description="Health check interval in seconds"
    )

    # Database settings
    database_url: str = Field(
        default="sqlite+aiosqlite:///app/data/db/assetripper.db",
        description="Database URL",
    )

    # File storage settings
    upload_dir: Path = Field(
        default=Path("/app/data/uploads"), description="Upload directory"
    )
    export_dir: Path = Field(
        default=Path("/app/data/exports"), description="Export directory"
    )

    # File cleanup settings
    file_retention_days: int = Field(
        default=30, description="File retention period in days"
    )
    cleanup_schedule_cron: str = Field(
        default="0 2 * * *", description="Cleanup schedule (cron format)"
    )

    # Task processing settings
    max_concurrent_tasks: int = Field(
        default=1, description="Maximum concurrent tasks"
    )
    task_timeout_seconds: int = Field(
        default=3600, description="Task timeout in seconds"
    )
    task_load_timeout: int = Field(
        default=300, description="LoadFile timeout in seconds"
    )
    task_export_timeout: int = Field(
        default=3600, description="Export timeout in seconds"
    )

    @property
    def assetripper_base_url(self) -> str:
        """Get AssetRipper base URL."""
        if self.assetripper_host:
            return self.assetripper_host
        return f"http://localhost:{self.assetripper_port}"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.export_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
