# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AssetRipper API Server is a FastAPI-based RESTful API that wraps the AssetRipper.GUI.Free tool for extracting Unity Assets from APK/XAPK/IPA files. It provides an HTTP API interface to a normally GUI-based application, with task queuing, health monitoring, and automatic file cleanup.

## Development Commands

### Local Development (macOS)

```bash
# Start server (foreground with auto-reload)
./start.sh

# Start server (background daemon mode)
./start.sh -d

# Stop server
./stop.sh

# Restart server (background mode)
./restart.sh

# View logs
tail -f logs/uvicorn.log  # HTTP server logs
tail -f logs/app.log       # Application logs
```

**Requirements**: Python 3.11+, AssetRipper macOS binary at `local/AssetRipper.GUI.Free`

### Using External AssetRipper Instance

If you encounter issues with the application starting AssetRipper, you can manually start it separately and configure the application to use it:

```bash
# 1. Start AssetRipper manually
cd local
./AssetRipper.GUI.Free --port 8765 --launch-browser=false

# 2. In another terminal, set environment variable and start the API server
export ASSETRIPPER_HOST=http://localhost:8765
./start.sh
```

Or add to your `.env` file:
```
ASSETRIPPER_HOST=http://localhost:8765
```

When `ASSETRIPPER_HOST` is set, the application will:
- Skip starting its own AssetRipper process
- Connect to the external instance at the specified URL
- Not attempt to restart or manage the external process
- Still perform health checks via HTTP

### Docker Deployment

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild after code changes
docker-compose build --no-cache
docker-compose up -d
```

### Testing the API

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Upload file
curl -X POST "http://localhost:8000/api/v1/upload" \
  -F "file=@/path/to/game.apk"

# Check task status
curl http://localhost:8000/api/v1/tasks/{task_id}

# Download exported assets
curl -O -J http://localhost:8000/api/v1/download/{task_id}
```

## Core Architecture

### Single AssetRipper Instance Pattern

**CRITICAL**: The entire system is designed around a **single, long-running AssetRipper.GUI.Free process** that is reused for all tasks:

- One AssetRipper instance starts with the application ([app/core/assetripper.py](app/core/assetripper.py:40-95))
- All file operations go through this single instance via HTTP
- The instance is managed by `AssetRipperManager` with health checks and auto-restart
- After each task, AssetRipper is reset (not restarted) to clear state

**Why**: AssetRipper startup is expensive (~5-10 seconds). Reusing one instance improves throughput dramatically.

### Sequential Task Processing

Tasks are processed **one at a time, in FIFO order** using `asyncio.Queue`:

- Queue managed by `TaskQueueManager` ([app/core/task_queue.py](app/core/task_queue.py:29-99))
- Worker coroutine runs continuously, pulling tasks from queue
- Only one task can be in `PROCESSING` state at any time
- Tasks interrupted by restart are auto-marked as `FAILED` on startup

**Why**: AssetRipper's `/Export/PrimaryContent` endpoint is synchronous and blocks. Sequential processing simplifies state management and prevents resource conflicts.

### Task Processing Flow

Each task goes through these steps:

1. **Upload** → File saved to `data/uploads/{task_id}/`
2. **Load** → `POST /LoadFile` to AssetRipper (async, ~5s for large files)
3. **Export** → `POST /Export/PrimaryContent` (sync, blocks until complete, can take minutes)
4. **Verify** → Check `data/exports/{task_id}/ExportedProject/Assets/` exists
5. **Reset** → `POST /Reset` to clear AssetRipper state for next task

ZIP archives are created **on-demand** during download, not during export, to save disk space.

### Database Schema

SQLite with two tables:
- `tasks`: Task tracking (id, status, file paths, timestamps, error messages)
- `cleanup_log`: Audit log for automated file cleanup

Task statuses: `PENDING` → `PROCESSING` → `COMPLETED`/`FAILED`

### Health Monitoring

- AssetRipper health checked every 30s via HTTP GET `/`
- Process crashes trigger auto-restart (max 5 attempts with exponential backoff)
- Health status exposed via `/api/v1/health` endpoint

## Important Constraints

### Python Version Compatibility

**CRITICAL**: Use SQLAlchemy >= 2.0.36 and aiosqlite >= 0.20.0 for Python 3.13+ compatibility. Earlier versions (2.0.25, 0.19.0) will fail with typing errors.

### AssetRipper Binary Platform

The AssetRipper binary **must match the deployment platform**:
- Local macOS development: macOS binary in `local/AssetRipper.GUI.Free`
- Docker: Linux binary in `bin/AssetRipper.GUI.Free` (copied into image)

### Blocking Export Operation

AssetRipper's `/Export/PrimaryContent` is **synchronous** and can take 30+ minutes for large games:
- Uses 1-hour timeout (`TASK_EXPORT_TIMEOUT=3600`)
- **Do not** make this endpoint async or parallel - AssetRipper doesn't support it
- Progress cannot be queried mid-export

### File Path Management

All file paths are absolute and dynamically constructed:
- Upload: `{UPLOAD_DIR}/{task_id}/{original_filename}`
- Export: `{EXPORT_DIR}/{task_id}/ExportedProject/Assets/`
- Database URLs, log paths all use absolute paths

Never use relative paths in task processing.

### Docker Volume Mounts

Docker uses **local directory mounts**, not named volumes:
```yaml
volumes:
  - ./data/uploads:/app/data/uploads
  - ./data/exports:/app/data/exports
  - ./data/db:/app/data/db
  - ./logs:/app/logs
```

**Do not** create these directories in Dockerfile - they're mapped at runtime.

## Configuration

Environment variables are managed via `app/config.py` using `pydantic-settings`:

**Key settings**:
- `ASSETRIPPER_HOST`: External AssetRipper URL (e.g., `http://localhost:8765`). If set, the application will connect to this external instance instead of starting its own process. Useful when AssetRipper startup is problematic.
- `ASSETRIPPER_BINARY_PATH`: Path to AssetRipper binary (only used if `ASSETRIPPER_HOST` is not set)
- `ASSETRIPPER_PORT`: Internal HTTP port (default 8765, only used if `ASSETRIPPER_HOST` is not set)
- `DATABASE_URL`: SQLite connection string
- `FILE_RETENTION_DAYS`: Auto-cleanup threshold (default 30)
- `TASK_EXPORT_TIMEOUT`: Max export duration (default 3600s)

All settings have defaults and can be overridden via `.env` or environment variables.

## Deployment Differences

| Aspect | Local (macOS) | Docker |
|--------|--------------|--------|
| Binary | `local/AssetRipper.GUI.Free` (macOS) | `bin/AssetRipper.GUI.Free` (Linux) |
| Hot Reload | ✅ Yes (`--reload`) | ❌ No |
| Data Location | `./data/`, `./logs/` | Mapped volumes |
| Best For | Development/debugging | Production |

## Known Issues

### AssetRipper Hanging

AssetRipper may hang indefinitely on certain asset files during export:
- Process stays alive but stops making progress
- No error message, just gets stuck
- **Workaround**: This is an AssetRipper limitation, not an API bug
- Monitoring: Health checks continue passing (process is alive)
- Solution: Manual intervention required (stop/restart service)

### Startup Race Condition

AssetRipper takes ~2-3 seconds to start its HTTP server:
- Application waits via polling loop with 30s timeout
- First few health checks will return 502 - this is normal
- Only fail if no 200 response within timeout

## File Structure Notes

- **app/core/**: Core business logic (AssetRipper manager, task queue, file cleanup)
- **app/api/v1/endpoints/**: API route handlers
- **app/models.py**: SQLAlchemy ORM models
- **app/schemas.py**: Pydantic request/response models
- **app/config.py**: Centralized configuration via pydantic-settings
- **app/database.py**: Async SQLAlchemy setup with session management

## Debugging Tips

1. **Task stuck in PROCESSING**: Check AssetRipper process (`ps aux | grep AssetRipper`) and logs (`logs/app.log.assetripper`)
2. **Database locked errors**: SQLite doesn't handle high concurrency well - check for abandoned transactions
3. **Export directory empty**: Verify AssetRipper successfully loaded the file (check logs for "File loaded successfully")
4. **Permission errors (macOS)**: Run `xattr -d com.apple.quarantine local/AssetRipper.GUI.Free` to allow execution
