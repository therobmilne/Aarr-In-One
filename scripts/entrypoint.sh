#!/bin/bash
set -e

echo "========================================="
echo "  MediaForge v2 starting..."
echo "  Unified frontend for arr stack"
echo "========================================="

# Timezone
if [ -n "$TZ" ] && [ -f "/usr/share/zoneinfo/$TZ" ]; then
    ln -sf "/usr/share/zoneinfo/$TZ" /etc/localtime
fi

# Create directory structure
mkdir -p /config/db /config/logs

# uvicorn needs lowercase log level
LOG_LEVEL_LOWER=$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')

echo "Starting web server on port ${APP_PORT:-8686}..."
exec python -m uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port "${APP_PORT:-8686}" \
    --log-level "$LOG_LEVEL_LOWER"
