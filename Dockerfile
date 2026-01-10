# =============================================================================
# Packet Inspection Transformer - Main Application Dockerfile
# =============================================================================
# Production-ready Docker image for the malware detection backend
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install build dependencies
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Install system dependencies for PyTorch
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download and install PyTorch with CUDA support (if available)
# Note: For CPU-only, use cpu tag or remove --index-url
ARG PYTORCH_VERSION=2.1.0
ARG CUDA_VERSION=12.1

# Install PyTorch
RUN pip download --no-deps \
    "torch==${PYTORCH_VERSION}" \
    "torchvision==0.16.0" \
    --platform manylinux_2014_x86_64 --only-binary=:all: \
    -f https://download.pytorch.org/whl/torch_stable.html || \
    pip install "torch==${PYTORCH_VERSION}" --index-url https://download.pytorch.org/whl/cu${CUENCY} || \
    pip install "torch==${PYTORCH_VERSION}"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Production - Minimal runtime image
# -----------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS production

# Security: Create non-root user
ARG APP_USER=appuser
ARG APP_UID=1000

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create user with specific UID/GID for security
RUN groupadd --gid ${APP_UID} ${APP_USER} 2>/dev/null || true
RUN useradd --uid ${APP_UID} --gid ${APP_UID} --create-home --shell /bin/bash ${APP_USER} 2>/dev/null || true

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_USER=${APP_USER} \
    APP_UID=${APP_UID}

# Copy application code from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application files
COPY --chown=${APP_USER}:${APP_USER} app.py .
COPY --chown=${APP_USER}:${APP_USER} settings.py .
COPY --chown=${APP_USER}:${APP_USER} models.py .
COPY --chown=${APP_USER}:${APP_USER} detector.py .
COPY --chown=${APP_USER}:${APP_USER} threat_manager.py .
COPY --chown=${APP_USER}:${APP_USER} database.py .
COPY --chown=${APP_USER}:${APP_USER} config/ ./config/
COPY --chown=${APP_USER}:${APP_USER} model/ ./model/

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data /app/certificates && \
    chown -R ${APP_USER}:${APP_USER} /app

# Switch to non-root user
USER ${APP_USER}

# Expose port (default for uvicorn)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

# Labels for container metadata
LABEL maintainer="security-team" \
      version="1.0.0" \
      description="Real-Time Malware Detection Gateway" \
      org.opencontainers.image.source="https://github.com/your-org/packet-inspection-transformer"