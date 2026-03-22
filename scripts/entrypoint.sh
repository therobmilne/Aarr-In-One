#!/bin/bash
set -e

echo "========================================="
echo "  MediaForge starting..."
echo "========================================="

# Timezone
if [ -n "$TZ" ] && [ -f "/usr/share/zoneinfo/$TZ" ]; then
    ln -sf "/usr/share/zoneinfo/$TZ" /etc/localtime
fi

# Create directory structure
#   /media/movies        - Downloaded movies (torrent/usenet)
#   /media/tv            - Downloaded TV shows (torrent/usenet)
#   /media/iptv-movies   - IPTV VOD movies (strm files)
#   /media/iptv-shows    - IPTV VOD TV shows (strm files)
#   /media/recordings    - Live TV DVR recordings
mkdir -p /config/db /config/vpn /config/logs \
    /downloads/torrents /downloads/usenet /downloads/complete \
    /media/movies /media/tv \
    /media/iptv-movies /media/iptv-shows \
    /media/recordings

# uvicorn needs lowercase log level
LOG_LEVEL_LOWER=$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')

echo "Starting web server on port ${APP_PORT:-8686}..."
exec python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "${APP_PORT:-8686}" \
    --log-level "$LOG_LEVEL_LOWER"
