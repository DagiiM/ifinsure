# =============================================================================
# iFinsure - Production Dockerfile
# =============================================================================
#
# Multi-stage build for optimized production image
# 
# Build: docker build -t ifinsure:latest -f provisioning/Dockerfile .
# Run:   docker run -p 8000:8000 --env-file .env.production ifinsure:latest
#
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

# Set build-time environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install dependencies
COPY requirements/production.txt /tmp/requirements.txt
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /tmp/requirements.txt

# -----------------------------------------------------------------------------
# Stage 2: Production Image
# -----------------------------------------------------------------------------
FROM python:3.11-slim as production

# Labels
LABEL maintainer="iFinsure Team <support@ifinsure.com>" \
      version="1.0.0" \
      description="iFinsure Insurance Management System"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_HOME=/app \
    # Gunicorn settings
    GUNICORN_WORKERS=4 \
    GUNICORN_THREADS=2 \
    GUNICORN_TIMEOUT=120

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Set work directory
WORKDIR ${APP_HOME}

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appgroup . .

# Create required directories
RUN mkdir -p ${APP_HOME}/staticfiles \
             ${APP_HOME}/media \
             ${APP_HOME}/logs \
    && chown -R appuser:appgroup ${APP_HOME}

# Create health check endpoint
RUN echo 'from django.http import JsonResponse; health_check = lambda r: JsonResponse({"status": "healthy"})' > ${APP_HOME}/apps/core/health.py

# Switch to non-root user
USER appuser

# Collect static files (will be overwritten during deployment)
RUN python manage.py collectstatic --noinput || true

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Default command
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--threads", "2", "--timeout", "120"]
