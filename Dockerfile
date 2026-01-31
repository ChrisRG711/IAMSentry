# IAMSentry Dockerfile
# Multi-stage build for a minimal, secure container

# ============================================
# Stage 1: Builder
# ============================================
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (better layer caching)
COPY pyproject.toml requirements.txt ./

# Install dependencies to user site-packages
RUN pip install --user --no-cache-dir -r requirements.txt

# Copy and install the application
COPY IAMSentry/ ./IAMSentry/
COPY README.md ./
RUN pip install --user --no-cache-dir -e ".[dashboard]"

# ============================================
# Stage 2: Runtime
# ============================================
FROM python:3.11-slim

# Labels
LABEL org.opencontainers.image.title="IAMSentry"
LABEL org.opencontainers.image.description="GCP IAM Security Auditor and Remediation Tool"
LABEL org.opencontainers.image.source="https://github.com/ChrisRG711/IAMSentry"
LABEL org.opencontainers.image.version="0.4.0"
LABEL org.opencontainers.image.licenses="MIT"

# Create non-root user for security
RUN groupadd -r iamsentry && useradd -r -g iamsentry -d /app -s /sbin/nologin iamsentry

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /home/iamsentry/.local

# Copy application code
COPY --chown=iamsentry:iamsentry IAMSentry/ /app/IAMSentry/
COPY --chown=iamsentry:iamsentry config.template.yaml /app/
COPY --chown=iamsentry:iamsentry README.md /app/

# Create necessary directories
RUN mkdir -p /app/output /app/logs && \
    chown -R iamsentry:iamsentry /app

# Set environment
ENV PATH=/home/iamsentry/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV IAMSENTRY_DATA_DIR=/app/output

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')" || exit 1

# Switch to non-root user
USER iamsentry

# Expose dashboard port
EXPOSE 8080

# Default entrypoint: dashboard
ENTRYPOINT ["python", "-m", "IAMSentry.dashboard.server"]
CMD ["--host", "0.0.0.0", "--port", "8080"]
