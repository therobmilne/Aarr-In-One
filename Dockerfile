# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

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

# Install Python deps via requirements.txt (simpler than pyproject.toml in Docker)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY backend/ ./backend/
COPY alembic.ini ./
COPY scripts/ ./scripts/
RUN chmod +x scripts/*.sh

# Copy frontend build
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

RUN mkdir -p /config/db /config/vpn /config/logs \
    /downloads/torrents /downloads/usenet /downloads/complete \
    /media/movies /media/tv /media/recordings

EXPOSE 8686
VOLUME ["/config", "/downloads", "/media"]

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8686/api/v1/system/health || exit 1

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
