"""AssetRipper process manager."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AssetRipperError(Exception):
    """Base exception for AssetRipper errors."""

    pass


class AssetRipperConnectionError(AssetRipperError):
    """Raised when cannot connect to AssetRipper."""

    pass


class AssetRipperProcessError(AssetRipperError):
    """Raised when AssetRipper process fails."""

    pass


class AssetRipperManager:
    """
    Manager for AssetRipper.GUI.Free process.

    Handles starting, stopping, health checking, and communicating
    with a single long-running AssetRipper instance.
    """

    def __init__(self):
        """Initialize AssetRipper manager."""
        self.process: Optional[asyncio.subprocess.Process] = None
        self.client: Optional[httpx.AsyncClient] = None
        self.health_check_task: Optional[asyncio.Task] = None
        self._is_healthy = False
        self._restart_count = 0
        self._max_restarts = 5
        self._use_external_host = bool(settings.assetripper_host)

    async def start(self) -> None:
        """
        Start AssetRipper process and wait for it to be ready.

        Raises:
            AssetRipperProcessError: If process fails to start
        """
        if self._use_external_host:
            logger.info(f"Using external AssetRipper at {settings.assetripper_host}")
        else:
            logger.info("Starting AssetRipper process...")

            # Build command
            cmd = [
                settings.assetripper_binary_path,
                "--port",
                str(settings.assetripper_port),
                "--launch-browser=false",
                "--log",
            ]

            if settings.log_file:
                cmd.extend(["--log-path", f"{settings.log_file}.assetripper"])

            # Start process
            try:
                self.process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                logger.info(f"AssetRipper process started with PID {self.process.pid}")
            except Exception as e:
                raise AssetRipperProcessError(f"Failed to start AssetRipper: {e}")

        # Initialize HTTP client
        self.client = httpx.AsyncClient(
            base_url=settings.assetripper_base_url,
            timeout=httpx.Timeout(600.0, connect=10.0),
        )

        # Wait for AssetRipper to be ready
        await self._wait_for_ready()

        # Start health check loop
        self.health_check_task = asyncio.create_task(self._health_check_loop())

        logger.info("AssetRipper is ready")

    async def stop(self) -> None:
        """Stop AssetRipper process gracefully."""
        logger.info("Stopping AssetRipper...")

        # Stop health check
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        # Close HTTP client
        if self.client:
            await self.client.aclose()
            self.client = None

        # Stop process (only if we started it)
        if not self._use_external_host and self.process and self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=30.0)
                logger.info("AssetRipper stopped gracefully")
            except asyncio.TimeoutError:
                logger.warning("AssetRipper did not stop gracefully, killing...")
                self.process.kill()
                await self.process.wait()
                logger.info("AssetRipper killed")

        self.process = None
        self._is_healthy = False

    async def is_healthy(self) -> bool:
        """
        Check if AssetRipper is healthy.

        Returns:
            bool: True if healthy, False otherwise
        """
        return self._is_healthy

    async def load_file(self, file_path: str) -> None:
        """
        Load a file into AssetRipper.

        Args:
            file_path: Absolute path to the file to load

        Raises:
            AssetRipperConnectionError: If cannot communicate with AssetRipper
            AssetRipperError: If load operation fails
        """
        if not self.client:
            raise AssetRipperConnectionError("AssetRipper client not initialized")

        logger.info(f"Loading file: {file_path}")

        try:
            response = await self.client.post(
                "/LoadFile",
                data={"path": file_path},
                timeout=settings.task_load_timeout,
                follow_redirects=True,
            )
            response.raise_for_status()
            logger.info(f"File loaded successfully: {file_path}")
        except httpx.TimeoutException as e:
            raise AssetRipperError(f"LoadFile timeout: {e}")
        except httpx.HTTPStatusError as e:
            raise AssetRipperError(f"LoadFile failed with status {e.response.status_code}: {e}")
        except httpx.RequestError as e:
            raise AssetRipperConnectionError(f"LoadFile request failed: {e}")

    async def export_primary_content(self, export_path: str) -> None:
        """
        Export primary content (Assets) from AssetRipper.

        This is a synchronous operation that blocks until export completes.

        Args:
            export_path: Absolute path to export directory

        Raises:
            AssetRipperConnectionError: If cannot communicate with AssetRipper
            AssetRipperError: If export operation fails
        """
        if not self.client:
            raise AssetRipperConnectionError("AssetRipper client not initialized")

        logger.info(f"Exporting to: {export_path}")

        # Ensure export directory exists
        Path(export_path).mkdir(parents=True, exist_ok=True)

        try:
            response = await self.client.post(
                "/Export/PrimaryContent",
                data={"path": export_path},
                timeout=settings.task_export_timeout,
                follow_redirects=True,
            )
            response.raise_for_status()
            logger.info(f"Export completed successfully: {export_path}")
        except httpx.TimeoutException as e:
            raise AssetRipperError(f"Export timeout: {e}")
        except httpx.HTTPStatusError as e:
            raise AssetRipperError(f"Export failed with status {e.response.status_code}: {e}")
        except httpx.RequestError as e:
            raise AssetRipperConnectionError(f"Export request failed: {e}")

    async def reset(self) -> None:
        """Reset AssetRipper to clear loaded files."""
        if not self.client:
            raise AssetRipperConnectionError("AssetRipper client not initialized")

        logger.info("Resetting AssetRipper...")

        try:
            response = await self.client.post("/Reset", follow_redirects=True)
            response.raise_for_status()
            logger.info("AssetRipper reset successfully")
        except Exception as e:
            logger.warning(f"Failed to reset AssetRipper: {e}")

    async def _wait_for_ready(self) -> None:
        """
        Wait for AssetRipper to be ready by polling the health endpoint.

        Raises:
            AssetRipperProcessError: If AssetRipper doesn't become ready in time
        """
        logger.info("Waiting for AssetRipper to be ready...")

        start_time = asyncio.get_event_loop().time()
        timeout = settings.assetripper_startup_timeout

        while True:
            # Check if process is still running (only if we started it)
            if not self._use_external_host and self.process and self.process.returncode is not None:
                raise AssetRipperProcessError(
                    f"AssetRipper process died with code {self.process.returncode}"
                )

            # Check timeout
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise AssetRipperProcessError(
                    f"AssetRipper did not become ready within {timeout} seconds"
                )

            # Try to connect
            try:
                response = await self.client.get("/", timeout=5.0)
                if response.status_code == 200:
                    self._is_healthy = True
                    return
            except (httpx.RequestError, httpx.TimeoutException):
                pass

            # Wait before retry
            await asyncio.sleep(1)

    async def _health_check_loop(self) -> None:
        """Background task to periodically check AssetRipper health."""
        interval = settings.assetripper_health_check_interval

        while True:
            try:
                await asyncio.sleep(interval)

                # Check process is alive (only if we started it)
                if not self._use_external_host:
                    if not self.process or self.process.returncode is not None:
                        logger.error("AssetRipper process is not running")
                        self._is_healthy = False
                        await self._attempt_restart()
                        continue

                # HTTP health check
                try:
                    response = await self.client.get("/", timeout=5.0)
                    if response.status_code == 200:
                        self._is_healthy = True
                    else:
                        logger.warning(f"AssetRipper health check failed: status {response.status_code}")
                        self._is_healthy = False
                except (httpx.RequestError, httpx.TimeoutException) as e:
                    logger.warning(f"AssetRipper health check failed: {e}")
                    self._is_healthy = False
                    if not self._use_external_host:
                        await self._attempt_restart()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error in health check loop: {e}")

    async def _attempt_restart(self) -> None:
        """Attempt to restart AssetRipper process."""
        if self._restart_count >= self._max_restarts:
            logger.error(f"Max restart attempts ({self._max_restarts}) reached, giving up")
            return

        self._restart_count += 1
        logger.info(f"Attempting to restart AssetRipper (attempt {self._restart_count}/{self._max_restarts})...")

        try:
            await self.stop()
            await asyncio.sleep(2 ** self._restart_count)  # Exponential backoff
            await self.start()
            self._restart_count = 0  # Reset counter on successful restart
            logger.info("AssetRipper restarted successfully")
        except Exception as e:
            logger.exception(f"Failed to restart AssetRipper: {e}")


# Global AssetRipper manager instance
assetripper_manager = AssetRipperManager()
