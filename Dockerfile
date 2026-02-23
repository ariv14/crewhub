# Multi-stage build optimized for Cloud Run
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN pip install --no-cache-dir hatchling

# Copy only dependency files first (better layer caching)
COPY pyproject.toml .
COPY src/__init__.py src/__init__.py

# Install production dependencies
RUN pip install --no-cache-dir .

# --- Production stage ---
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

# Cloud Run uses PORT env var (default 8080)
ENV PORT=8080

EXPOSE ${PORT}

# Cloud Run requires the container to listen on 0.0.0.0:$PORT
CMD exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT} --workers 1
