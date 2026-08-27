#!/usr/bin/env bash
set -e

echo "Starting production boot sequence..."

echo "1. Running database migrations..."
alembic upgrade head

echo "2. Running database seeder..."
python -m app.db.seed

echo "3. Starting web server..."
# PORT is typically supplied by Render / Railway dynamically
export PORT=${PORT:-8000}
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
