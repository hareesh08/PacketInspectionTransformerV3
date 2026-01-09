# ============================================================================
# Packet Inspection Transformer - Multi-Stage Production Dockerfile
# ============================================================================

# ----------------------------------------------------------------------------
# Build Stage: Install Python dependencies
# ----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies in isolated location
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ----------------------------------------------------------------------------
# Model Download Stage
# ----------------------------------------------------------------------------
FROM builder AS model-downloader

WORKDIR /model

# Model configuration
ARG MODEL_VERSION="latest"
ARG GITHUB_REPOSITORY=""
ENV MODEL_PATH="model/finetuned_best_model.pth"

# Download model from GitHub releases (if available)
RUN if [ -n "${GITHUB_REPOSITORY}" ] && [ "${MODEL_VERSION}" != "none" ]; then \
    echo "Downloading model version ${MODEL_VERSION} from ${GITHUB_REPOSITORY}..." && \
    MODEL_URL="https://github.com/${GITHUB_REPOSITORY}/releases/download/model-${MODEL_VERSION}/finetuned_best_model.pth" && \
    curl -L -o ${MODEL_PATH} \
      -H "Accept: application/octet-stream" \
      "${MODEL_URL}" || echo "Model download failed, will use fallback"; \
  else \
    echo "No model download configured, will use local copy"; \
  fi

# ----------------------------------------------------------------------------
# Runtime Stage: Minimal production image
# ----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Install minimal runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY --chown=appuser:appuser . .

# Ensure model directory exists
RUN mkdir -p /app/model

# Copy model file if it doesn't exist in the copied application code
# Model should be included via LFS during build context
RUN if [ ! -f /app/model/finetuned_best_model.pth ]; then \
    echo "WARNING: Model file not found in build context"; \
  else \
    echo "Model file found: $(ls -lh /app/model/finetuned_best_model.pth)"; \
  fi

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]