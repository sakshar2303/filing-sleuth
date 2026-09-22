# ── Stage 1: Build ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies for native packages (thefuzz[speedup], lxml, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy only dependency spec first for layer caching
COPY pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install .

# ── Stage 2: Runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY backend/ ./backend/
COPY evaluation/ ./evaluation/
COPY pyproject.toml ./

# Create cache directory
RUN mkdir -p /app/cache_data

# Render sets PORT dynamically
ENV PORT=8000

EXPOSE ${PORT}

# Run the FastAPI server
CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}
