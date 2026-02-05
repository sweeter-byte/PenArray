# Dockerfile for BiZhen Backend
# Multi-stage build for optimized image size

# ============================================
# Stage 1: Builder - Install dependencies
# ============================================
FROM python:3.10-slim as builder

WORKDIR /app

# Install build dependencies
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources || true
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Pre-install CPU-only PyTorch (Small 175MB version)
# Use huge timeout (3600s) because download.pytorch.org is slow in China
RUN pip install --default-timeout=3600 --user --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install Python dependencies to user directory
RUN pip install --user --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# ============================================
# Stage 2: Runtime - Final image
# ============================================
FROM python:3.10-slim

WORKDIR /app

# Install runtime dependencies only
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources || true
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    tesseract-ocr \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /root/.local /root/.local

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Set Python path for module imports
ENV PYTHONPATH=/app:$PYTHONPATH

# Copy application code
COPY . .

# Make startup script executable
RUN chmod +x /app/start.sh

# Expose API port
EXPOSE 8000

# Default command - can be overridden in docker-compose for worker
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
