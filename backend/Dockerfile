# Dockerfile for BiZhen Backend
# Multi-stage build for optimized image size

# ============================================
# Stage 1: Builder - Install dependencies
# ============================================
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies to user directory
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: Runtime - Final image
# ============================================
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Set Python path for module imports
ENV PYTHONPATH=/app:$PYTHONPATH

# Copy application code
COPY . .

# Expose API port
EXPOSE 8000

# Default command - can be overridden in docker-compose for worker
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
