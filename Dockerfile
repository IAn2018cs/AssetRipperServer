FROM python:3.11-slim-bookworm

# Set working directory
WORKDIR /app

# Install system dependencies for AssetRipper binary
RUN apt-get update && apt-get install -y \
    libicu72 \
    libssl3 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy AssetRipper binary and library
COPY bin/AssetRipper.GUI.Free /app/bin/
COPY bin/libcapstone.so /app/bin/
RUN chmod +x /app/bin/AssetRipper.GUI.Free

# Copy application code
COPY app/ /app/app/

# Copy entrypoint script
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose FastAPI port (not AssetRipper internal port)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health').read()" || exit 1

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]
