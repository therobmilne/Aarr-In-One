#!/bin/bash
set -e

echo "========================================="
echo "  MediaForge starting..."
echo "========================================="

# Timezone
if [ -n "$TZ" ] && [ -f "/usr/share/zoneinfo/$TZ" ]; then
    ln -sf "/usr/share/zoneinfo/$TZ" /etc/localtime
fi

# Directories
mkdir -p /config/db /config/vpn /config/logs \
    /downloads/torrents /downloads/usenet /downloads/complete \
    /media/movies /media/tv /media/recordings

echo "Starting web server on port ${APP_PORT:-8686}..."
exec python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "${APP_PORT:-8686}" \
    --log-level "${LOG_LEVEL:-info}"
