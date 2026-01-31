#!/bin/bash
# BiZhen Backend Startup Script
#
# This script:
# 1. Waits for PostgreSQL to be ready
# 2. Initializes the database (creates tables + seeds admin user)
# 3. Starts the FastAPI server
#
# Usage: ./start.sh

set -e

echo "=========================================="
echo "BiZhen Backend Startup"
echo "=========================================="

# Wait for PostgreSQL to be ready (max 30 seconds)
echo "Waiting for PostgreSQL..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python -c "
from sqlalchemy import create_engine
from backend.config import settings
engine = create_engine(settings.db_url)
conn = engine.connect()
conn.close()
print('Database is ready!')
" 2>/dev/null; then
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "Waiting for database... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 1
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "ERROR: Could not connect to database after $MAX_RETRIES seconds"
    exit 1
fi

# Initialize database (create tables + seed admin user)
echo ""
echo "Initializing database..."
python -m backend.db.init_db

# Start the FastAPI server
echo ""
echo "Starting FastAPI server..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
