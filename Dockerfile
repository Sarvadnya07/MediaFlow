# Multi-stage production Dockerfile for MediaFlow Headless Backend & Worker
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install minimal OS dependencies including ffmpeg for media remuxing/transcoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies in isolated layer
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create unprivileged application user
RUN groupadd -g 1000 mediaflow && \
    useradd -u 1000 -g mediaflow -s /bin/bash -m mediaflow && \
    mkdir -p /app/downloads && \
    chown -R mediaflow:mediaflow /app

# Copy application code with proper ownership
COPY --chown=mediaflow:mediaflow . .

USER mediaflow

# Expose FastAPI HTTP/WebSocket port
EXPOSE 8000

# Healthcheck for orchestration
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/docs || exit 1

# Default entrypoint runs database migrations then boots uvicorn server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
