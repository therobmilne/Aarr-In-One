# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build && ls -la dist/ && echo "Frontend build SUCCESS"

# Stage 2: Python runtime
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wireguard-tools \
    openvpn \
    iptables \
    ffmpeg \
    par2 \
    unrar-free \
    mediainfo \
    iproute2 \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright's Chromium browser (for Cloudflare bypass)
RUN playwright install --with-deps chromium 2>/dev/null || echo "Playwright browser install skipped"

COPY backend/ ./backend/
COPY alembic.ini ./
COPY scripts/ ./scripts/
RUN chmod +x scripts/*.sh

# Copy frontend build and verify
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
RUN ls -la frontend/dist/ && echo "Frontend dist copied OK"

RUN mkdir -p /config/db /config/vpn /config/logs \
    /downloads/torrents /downloads/usenet /downloads/complete \
    /media/movies /media/tv /media/iptv-movies /media/iptv-shows /media/recordings

EXPOSE 8686
VOLUME ["/config", "/downloads", "/media"]

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8686/api/v1/system/health || exit 1

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
