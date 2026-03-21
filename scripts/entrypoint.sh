#!/bin/bash
set -e

PUID=${PUID:-1000}
PGID=${PGID:-1000}

echo "MediaForge starting..."
echo "  PUID: $PUID"
echo "  PGID: $PGID"
echo "  TZ: ${TZ:-UTC}"

# Set timezone
if [ -n "$TZ" ] && [ -f "/usr/share/zoneinfo/$TZ" ]; then
    ln -sf "/usr/share/zoneinfo/$TZ" /etc/localtime
    echo "$TZ" > /etc/timezone
fi

# Ensure directories exist with correct permissions
mkdir -p /config/db /config/vpn /config/indexers /config/logs \
    /downloads/torrents /downloads/usenet /downloads/complete \
    /media/movies /media/tv /media/recordings

# Run database migrations
echo "Running database migrations..."
cd /app
python -m alembic upgrade head 2>/dev/null || echo "Migrations skipped (first run will use auto-create)"

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A backend.celery_app.celery worker \
    --loglevel=info \
    --concurrency=2 \
    -Q default \
    --without-heartbeat \
    --without-mingle &

# Start Celery Beat scheduler in background
echo "Starting Celery Beat..."
celery -A backend.celery_app.celery beat \
    --loglevel=info \
    --schedule=/config/celerybeat-schedule &

# Start the web server
echo "Starting MediaForge web server on port ${APP_PORT:-8686}..."
exec uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "${APP_PORT:-8686}" \
    --workers 1 \
    --log-level "${LOG_LEVEL:-info}" \
    --access-log
