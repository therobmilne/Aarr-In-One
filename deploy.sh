#!/bin/bash
set -e

# ============================================================
# MediaForge v2 — Full Deployment Script
# Run this on your HOST machine (not inside a container)
# ============================================================

PROJECT_DIR="/Users/robmilne/Aarr-In-One"
cd "$PROJECT_DIR"

echo ""
echo "=========================================="
echo "  MediaForge v2 — Full Stack Deployment"
echo "=========================================="
echo ""

# ----------------------------------------------------------
# Step 1: Stop everything that's running
# ----------------------------------------------------------
echo "[1/8] Stopping existing containers..."
docker compose down --remove-orphans 2>/dev/null || true
echo "  ✓ Containers stopped"

# ----------------------------------------------------------
# Step 2: Back up old config (safety net)
# ----------------------------------------------------------
BACKUP="config.backup.$(date +%Y%m%d_%H%M%S)"
if [ -d "config" ]; then
    echo "[2/8] Backing up existing config → $BACKUP"
    cp -r config "$BACKUP"
    echo "  ✓ Backup saved"
else
    echo "[2/8] No existing config to back up, skipping"
fi

# ----------------------------------------------------------
# Step 3: Create all config directories
# ----------------------------------------------------------
echo "[3/8] Creating config directories for all services..."
mkdir -p config/mediaforge/db
mkdir -p config/mediaforge/logs
mkdir -p config/radarr
mkdir -p config/sonarr
mkdir -p config/prowlarr
mkdir -p config/bazarr
mkdir -p config/qbittorrent
mkdir -p config/sabnzbd
mkdir -p config/gluetun
mkdir -p config/jellyseerr
mkdir -p config/threadfin

# Migrate old MediaForge DB if it exists in the old location
if [ -f "config/db/mediaforge.db" ] && [ ! -f "config/mediaforge/db/mediaforge.db" ]; then
    echo "  → Migrating old database to new location..."
    cp config/db/mediaforge.db config/mediaforge/db/mediaforge.db
fi

# Migrate old logs
if [ -d "config/logs" ] && [ ! "$(ls -A config/mediaforge/logs 2>/dev/null)" ]; then
    cp config/logs/* config/mediaforge/logs/ 2>/dev/null || true
fi

echo "  ✓ Directories ready"

# ----------------------------------------------------------
# Step 4: Ensure .env has VPN variables for Gluetun
# ----------------------------------------------------------
echo "[4/8] Checking .env file..."
if [ ! -f ".env" ]; then
    echo "  → Creating .env from template..."
    cp .env.example .env
    echo "  ⚠ Created .env — edit it with your API keys before the setup wizard"
fi

# Add missing VPN variables if .env exists but is from old version
if ! grep -q "VPN_PRIVATE_KEY" .env 2>/dev/null; then
    echo "" >> .env
    echo "# VPN (Gluetun) — added by deploy script" >> .env
    echo "VPN_PROVIDER=protonvpn" >> .env
    echo "VPN_TYPE=wireguard" >> .env
    echo "VPN_PRIVATE_KEY=" >> .env
    echo "VPN_ADDRESSES=" >> .env
    echo "VPN_COUNTRIES=Canada" >> .env
    echo "  → Added VPN variables to .env (fill in VPN_PRIVATE_KEY + VPN_ADDRESSES for VPN to work)"
fi

echo "  ✓ .env ready"

# ----------------------------------------------------------
# Step 5: Create /mnt/media and /mnt/downloads if missing
# ----------------------------------------------------------
echo "[5/8] Checking media/download mount points..."
if [ ! -d "/mnt/media" ]; then
    echo "  ⚠ /mnt/media does not exist!"
    echo "    Creating placeholder directories..."
    sudo mkdir -p /mnt/media/movies /mnt/media/tv /mnt/media/recordings 2>/dev/null || \
        mkdir -p /mnt/media/movies /mnt/media/tv /mnt/media/recordings 2>/dev/null || \
        echo "    ⚠ Could not create /mnt/media — you may need to update docker-compose.yml volume paths"
fi
if [ ! -d "/mnt/downloads" ]; then
    echo "  ⚠ /mnt/downloads does not exist!"
    sudo mkdir -p /mnt/downloads 2>/dev/null || \
        mkdir -p /mnt/downloads 2>/dev/null || \
        echo "    ⚠ Could not create /mnt/downloads — you may need to update docker-compose.yml volume paths"
fi
echo "  ✓ Mount points checked"

# ----------------------------------------------------------
# Step 6: Pull all third-party images
# ----------------------------------------------------------
echo "[6/8] Pulling all service images (this takes a few minutes)..."
docker compose pull
echo "  ✓ Images pulled"

# ----------------------------------------------------------
# Step 7: Build MediaForge
# ----------------------------------------------------------
echo "[7/8] Building MediaForge container..."
docker compose build --no-cache mediaforge
echo "  ✓ MediaForge built"

# ----------------------------------------------------------
# Step 8: Start everything
# ----------------------------------------------------------
echo "[8/8] Starting all services..."
docker compose up -d
echo "  ✓ All containers starting"

# ----------------------------------------------------------
# Wait for services and show status
# ----------------------------------------------------------
echo ""
echo "Waiting 30 seconds for services to initialize..."
sleep 30

echo ""
echo "=========================================="
echo "  Container Status"
echo "=========================================="
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=========================================="
echo "  🎉 MediaForge v2 is deployed!"
echo "=========================================="
echo ""
echo "  Open: http://$(hostname -I 2>/dev/null | awk '{print $1}' || echo 'your-ip'):8686"
echo ""
echo "  The setup wizard will guide you through:"
echo "    1. Connecting to Jellyfin"
echo "    2. Auto-configuring all backend services"
echo "    3. Setting up TMDB API key"
echo ""
echo "  Backend services (you never need to open these):"
echo "    Radarr:      http://localhost:7878  (not exposed by default)"
echo "    Sonarr:      http://localhost:8989  (not exposed by default)"
echo "    Prowlarr:    http://localhost:9696  (not exposed by default)"
echo "    qBittorrent: http://localhost:8080  (through Gluetun)"
echo "    SABnzbd:     http://localhost:8081  (through Gluetun)"
echo ""
echo "  ⚠ VPN: If you didn't set VPN_PRIVATE_KEY in .env,"
echo "    Gluetun won't connect and torrents won't download."
echo "    Configure VPN from the MediaForge UI → VPN page."
echo ""
echo "  Logs: docker compose logs -f mediaforge"
echo "  Stop: docker compose down"
echo ""
