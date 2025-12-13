#!/bin/bash
set -e

echo "Starting AssetRipper API Server..."

# Convert LOG_LEVEL to lowercase for uvicorn
LOG_LEVEL_LOWER=$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')

# Start FastAPI with uvicorn
exec uvicorn app.main:app \
    --host ${API_HOST:-0.0.0.0} \
    --port ${API_PORT:-8000} \
    --log-level ${LOG_LEVEL_LOWER}
