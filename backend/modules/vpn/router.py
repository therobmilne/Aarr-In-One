"""VPN API — proxies to Gluetun control server."""

import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.permissions import require_admin, require_power_user
from backend.logging_config import get_logger
from backend.models.user import User
from backend.services.arr_client import gluetun_request

logger = get_logger("vpn.router")

router = APIRouter(prefix="/vpn", tags=["vpn"])


class VPNConfig(BaseModel):
    provider: str = "protonvpn"
    connection_type: str = "wireguard"
    private_key: str | None = None
    addresses: str | None = None
    country: str = "Canada"
    # OpenVPN fields
    openvpn_username: str | None = None
    openvpn_password: str | None = None


@router.get("/status")
async def vpn_status(user: User = Depends(require_power_user)):
    """Check VPN connection status via Gluetun's control API."""
    try:
        ip_resp = await gluetun_request("GET", "/v1/publicip/ip")
        ip_data = ip_resp.json() if ip_resp.status_code == 200 else {}

        vpn_resp = await gluetun_request("GET", "/v1/openvpn/status")
        vpn_data = vpn_resp.json() if vpn_resp.status_code == 200 else {}

        return {
            "connected": True,
            "public_ip": ip_data.get("public_ip", "unknown"),
            "region": ip_data.get("region", "unknown"),
            "country": ip_data.get("country", "unknown"),
            "status": vpn_data.get("status", "unknown"),
        }
    except Exception:
        return {"connected": False, "public_ip": None, "region": None, "country": None}


@router.get("/config")
async def get_vpn_config(user: User = Depends(require_admin)):
    """Get current VPN configuration from .env file."""
    env_path = Path("/config/mediaforge/.env")
    config = {
        "provider": os.environ.get("VPN_PROVIDER", "protonvpn"),
        "connection_type": os.environ.get("VPN_TYPE", "wireguard"),
        "country": os.environ.get("VPN_COUNTRIES", "Canada"),
        "configured": env_path.exists(),
    }
    return config


@router.put("/config")
async def save_vpn_config(data: VPNConfig, user: User = Depends(require_admin)):
    """Save VPN configuration by updating the .env file.

    Note: After saving, the gluetun container needs to be restarted
    to pick up the new config. In a Docker environment, MediaForge
    can trigger this via `docker restart gluetun`.
    """
    env_path = Path("/config/mediaforge/.env")
    env_vars = {
        "VPN_PROVIDER": data.provider,
        "VPN_TYPE": data.connection_type,
        "VPN_COUNTRIES": data.country,
    }
    if data.private_key:
        env_vars["VPN_PRIVATE_KEY"] = data.private_key
    if data.addresses:
        env_vars["VPN_ADDRESSES"] = data.addresses

    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        with open(env_path, "w") as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
    except OSError as e:
        logger.warning("env_write_failed", error=str(e))
        return {"status": "saved_partial", "message": "Config saved but .env write failed"}

    return {"status": "saved", "message": "VPN configuration saved. Restart gluetun to apply."}


@router.post("/restart")
async def restart_vpn(user: User = Depends(require_admin)):
    """Restart gluetun to apply new VPN configuration."""
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "restart", "gluetun"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return {"status": "restarting", "message": "Gluetun is restarting with new configuration"}
        return {"status": "error", "message": result.stderr}
    except FileNotFoundError:
        return {"status": "error", "message": "Docker CLI not available (not running in Docker?)"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Restart timed out"}


@router.get("/port")
async def get_forwarded_port(user: User = Depends(require_power_user)):
    """Get VPN forwarded port from Gluetun."""
    try:
        resp = await gluetun_request("GET", "/v1/openvpn/portforwarded")
        if resp.status_code == 200:
            data = resp.json()
            return {"port": data.get("port", 0)}
    except Exception:
        pass
    return {"port": None}
