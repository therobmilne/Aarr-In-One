#!/bin/bash
set -e

# =============================================================================
# MediaForge Installer
# Run this inside a Proxmox LXC container (Debian/Ubuntu)
# =============================================================================

echo "========================================="
echo "  MediaForge Installer"
echo "========================================="
echo ""

# Check we're running as root
if [ "$EUID" -ne 0 ]; then
  echo "ERROR: Run this script as root (sudo ./install.sh)"
  exit 1
fi

# ---- Step 1: Install Docker ----
echo "[1/5] Installing Docker..."
if command -v docker &>/dev/null; then
  echo "  Docker already installed: $(docker --version)"
else
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg lsb-release

  # Add Docker repo
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg

  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null

  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  echo "  Docker installed: $(docker --version)"
fi

# ---- Step 2: Create /dev/net/tun if missing (needed for VPN) ----
echo "[2/5] Checking /dev/net/tun..."
if [ ! -c /dev/net/tun ]; then
  mkdir -p /dev/net
  mknod /dev/net/tun c 10 200
  chmod 666 /dev/net/tun
  echo "  Created /dev/net/tun"
else
  echo "  /dev/net/tun exists"
fi

# ---- Step 3: Create media directories ----
echo "[3/5] Creating media directories..."
mkdir -p /mnt/media/movies /mnt/media/tv /mnt/media/recordings
mkdir -p /mnt/downloads/torrents /mnt/downloads/usenet /mnt/downloads/complete
echo "  /mnt/media and /mnt/downloads ready"

# ---- Step 4: Clone or update MediaForge ----
echo "[4/5] Getting MediaForge..."
INSTALL_DIR="/opt/mediaforge"

if [ -d "$INSTALL_DIR/.git" ]; then
  echo "  Updating existing install..."
  cd "$INSTALL_DIR"
  git pull origin main
else
  echo "  Cloning from GitHub..."
  apt-get install -y -qq git
  git clone https://github.com/therobmilne/Aarr-In-One.git "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

# ---- Step 5: Build and start ----
echo "[5/5] Building and starting MediaForge + Jellyfin..."
echo "  This takes 3-5 minutes on first run..."
echo ""

docker compose up -d --build

echo ""
echo "========================================="
echo "  MediaForge is starting!"
echo "========================================="
echo ""

# Wait for services to be ready
echo "Waiting for services to come online..."
sleep 10

# Get the LXC IP
LXC_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "========================================="
echo "  READY!"
echo "========================================="
echo ""
echo "  Jellyfin:    http://${LXC_IP}:8096"
echo "  MediaForge:  http://${LXC_IP}:8686"
echo ""
echo "  FIRST TIME SETUP:"
echo "  1. Open Jellyfin at http://${LXC_IP}:8096"
echo "     Create your admin account (if new install)"
echo ""
echo "  2. Open MediaForge at http://${LXC_IP}:8686"
echo "     The setup wizard will walk you through"
echo "     connecting Jellyfin and configuring everything."
echo ""
echo "  Your media files should be at /mnt/media"
echo "  Your downloads will go to /mnt/downloads"
echo ""
echo "  To check logs:  cd /opt/mediaforge && docker compose logs -f"
echo "  To restart:     cd /opt/mediaforge && docker compose restart"
echo "  To stop:        cd /opt/mediaforge && docker compose down"
echo "========================================="
