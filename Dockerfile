# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build && ls -la dist/ && echo "Frontend build SUCCESS"

# Stage 2: Python runtime
FROM python:3.12-slim

# Minimal system dependencies — no VPN/torrent tools needed
# (those are handled by dedicated containers in the arr stack)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY alembic.ini ./
COPY scripts/ ./scripts/
RUN chmod +x scripts/*.sh

# Copy frontend build
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
RUN ls -la frontend/dist/ && echo "Frontend dist copied OK"

# Create minimal directory structure
# (most paths are mounted from Docker volumes)
RUN mkdir -p /config/db /config/logs

EXPOSE 8686
VOLUME ["/config", "/downloads", "/media"]

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8686/api/v1/system/health || exit 1

ENTRYPOINT ["/app/scripts/entrypoint.sh"]
