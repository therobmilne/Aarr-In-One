import re
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.permissions import require_admin, require_power_user
from backend.database import get_db
from backend.models.user import User
from backend.modules.vpn.schemas import VPNCredentials, VPNStatusResponse
from backend.modules.vpn.service import vpn_engine
from backend.services import settings_service

router = APIRouter(prefix="/vpn", tags=["vpn"])

VPN_CONFIG_DIR = Path("/config/vpn")

# Keys stored in the database under the "vpn" category
VPN_SETTINGS_KEYS = [
    "vpn_provider",
    "vpn_connection_type",
    "vpn_wireguard_config",
    "vpn_openvpn_username",
    "vpn_openvpn_password",
    "vpn_openvpn_config",
    "vpn_openvpn_server",
    "vpn_openvpn_port",
    "vpn_openvpn_protocol",
    "vpn_kill_switch",
    "vpn_port_forwarding",
]


def _mask_value(value: str | None, visible_chars: int = 4) -> str | None:
    """Mask sensitive string values, keeping only the last few characters."""
    if value is None or len(value) <= visible_chars:
        return value
    return "*" * 8 + value[-visible_chars:]


def _mask_wireguard_config(config: str | None) -> str | None:
    """Mask PrivateKey values in WireGuard config."""
    if config is None:
        return None
    return re.sub(
        r"(PrivateKey\s*=\s*)(\S+)",
        r"\1********",
        config,
    )


def _mask_openvpn_config(config: str | None) -> str | None:
    """Mask inline keys/certs in OpenVPN config."""
    if config is None:
        return None
    # Mask contents between <key>...</key>, <cert>...</cert>, <tls-auth>...</tls-auth>
    masked = re.sub(
        r"(<(?:key|cert|tls-auth|tls-crypt|secret)>)(.*?)(</(?:key|cert|tls-auth|tls-crypt|secret)>)",
        r"\1\n********\n\3",
        config,
        flags=re.DOTALL,
    )
    return masked


@router.get("/status", response_model=VPNStatusResponse)
async def get_vpn_status(user: User = Depends(require_power_user)):
    return vpn_engine.get_status()


@router.get("/config")
async def get_vpn_config(db: AsyncSession = Depends(get_db)):
    """Get saved VPN configuration with sensitive values masked."""
    raw = {}
    for key in VPN_SETTINGS_KEYS:
        raw[key] = await settings_service.get_setting(db, key)

    # Build masked response
    return {
        "provider": raw.get("vpn_provider"),
        "connection_type": raw.get("vpn_connection_type"),
        "wireguard_config": _mask_wireguard_config(raw.get("vpn_wireguard_config")),
        "openvpn_username": raw.get("vpn_openvpn_username"),
        "openvpn_password": _mask_value(raw.get("vpn_openvpn_password")),
        "openvpn_config": _mask_openvpn_config(raw.get("vpn_openvpn_config")),
        "openvpn_server": raw.get("vpn_openvpn_server"),
        "openvpn_port": raw.get("vpn_openvpn_port"),
        "openvpn_protocol": raw.get("vpn_openvpn_protocol"),
        "kill_switch": raw.get("vpn_kill_switch", True),
        "port_forwarding": raw.get("vpn_port_forwarding", True),
        "configured": raw.get("vpn_provider") is not None,
    }


@router.put("/config")
async def save_vpn_config(
    creds: VPNCredentials,
    db: AsyncSession = Depends(get_db),
):
    """Save VPN configuration to database and write config files to /config/vpn/."""
    # Persist all credentials to the database
    await settings_service.set_setting(db, "vpn_provider", creds.provider, "vpn")
    await settings_service.set_setting(db, "vpn_connection_type", creds.connection_type, "vpn")
    await settings_service.set_setting(db, "vpn_wireguard_config", creds.wireguard_config, "vpn")
    await settings_service.set_setting(db, "vpn_openvpn_username", creds.openvpn_username, "vpn")
    await settings_service.set_setting(db, "vpn_openvpn_password", creds.openvpn_password, "vpn")
    await settings_service.set_setting(db, "vpn_openvpn_config", creds.openvpn_config, "vpn")
    await settings_service.set_setting(db, "vpn_openvpn_server", creds.openvpn_server, "vpn")
    await settings_service.set_setting(db, "vpn_openvpn_port", creds.openvpn_port, "vpn")
    await settings_service.set_setting(db, "vpn_openvpn_protocol", creds.openvpn_protocol, "vpn")
    await settings_service.set_setting(db, "vpn_kill_switch", creds.kill_switch, "vpn")
    await settings_service.set_setting(db, "vpn_port_forwarding", creds.port_forwarding, "vpn")

    # Ensure the config directory exists
    VPN_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    files_written = []

    if creds.connection_type == "wireguard":
        if creds.wireguard_config:
            wg_path = VPN_CONFIG_DIR / "wg0.conf"
            wg_path.write_text(creds.wireguard_config)
            wg_path.chmod(0o600)
            files_written.append(str(wg_path))

            # Update runtime settings so connect() uses the right path/type
            from backend.config import settings as app_settings
            app_settings.VPN_TYPE = "wireguard"
            app_settings.VPN_CONFIG_PATH = str(wg_path)
            app_settings.VPN_PROVIDER = creds.provider

    elif creds.connection_type == "openvpn":
        if creds.openvpn_config:
            ovpn_path = VPN_CONFIG_DIR / "client.ovpn"
            ovpn_content = creds.openvpn_config

            # If username/password provided, inject auth-user-pass directive
            if creds.openvpn_username and creds.openvpn_password:
                auth_path = VPN_CONFIG_DIR / "auth.txt"
                auth_path.write_text(f"{creds.openvpn_username}\n{creds.openvpn_password}\n")
                auth_path.chmod(0o600)
                files_written.append(str(auth_path))

                # Add auth-user-pass to config if not already present
                if "auth-user-pass" not in ovpn_content:
                    ovpn_content += f"\nauth-user-pass {auth_path}\n"

            ovpn_path.write_text(ovpn_content)
            ovpn_path.chmod(0o600)
            files_written.append(str(ovpn_path))

            from backend.config import settings as app_settings
            app_settings.VPN_TYPE = "openvpn"
            app_settings.VPN_CONFIG_PATH = str(ovpn_path)
            app_settings.VPN_PROVIDER = creds.provider

    return {
        "status": "saved",
        "connection_type": creds.connection_type,
        "provider": creds.provider,
        "files_written": files_written,
        "kill_switch": creds.kill_switch,
        "port_forwarding": creds.port_forwarding,
    }


@router.post("/connect")
async def connect_vpn(db: AsyncSession = Depends(get_db)):
    """Connect to VPN using saved configuration."""
    # Load config from database if runtime settings are not yet populated
    provider = await settings_service.get_setting(db, "vpn_provider")
    if provider:
        conn_type = await settings_service.get_setting(db, "vpn_connection_type", "wireguard")
        kill_switch = await settings_service.get_setting(db, "vpn_kill_switch", True)
        port_forwarding = await settings_service.get_setting(db, "vpn_port_forwarding", True)

        from backend.config import settings as app_settings
        app_settings.VPN_PROVIDER = provider
        app_settings.VPN_TYPE = conn_type

        if conn_type == "wireguard":
            app_settings.VPN_CONFIG_PATH = str(VPN_CONFIG_DIR / "wg0.conf")
        else:
            app_settings.VPN_CONFIG_PATH = str(VPN_CONFIG_DIR / "client.ovpn")

    success = await vpn_engine.connect()
    if success:
        # If port forwarding is enabled, try to get the forwarded port
        port = None
        pf_enabled = await settings_service.get_setting(db, "vpn_port_forwarding", True)
        if pf_enabled:
            port = await vpn_engine.get_forwarded_port()

        return {
            "status": "connected",
            "ip": vpn_engine.get_status().public_ip,
            "forwarded_port": port,
        }
    return {"status": "failed"}


@router.post("/disconnect")
async def disconnect_vpn():
    """Disconnect from VPN."""
    success = await vpn_engine.disconnect()
    return {"status": "disconnected" if success else "failed"}


@router.get("/port")
async def get_forwarded_port(user: User = Depends(require_power_user)):
    port = await vpn_engine.get_forwarded_port()
    return {"port": port}


@router.post("/port/refresh")
async def refresh_forwarded_port(db: AsyncSession = Depends(get_db)):
    """Trigger a port forwarding refresh with the VPN provider."""
    if not vpn_engine.is_connected:
        return {"status": "error", "message": "VPN is not connected"}

    pf_enabled = await settings_service.get_setting(db, "vpn_port_forwarding", True)
    if not pf_enabled:
        return {"status": "error", "message": "Port forwarding is disabled in VPN config"}

    port = await vpn_engine.get_forwarded_port()
    if port:
        return {"status": "ok", "port": port}
    return {"status": "error", "message": "Failed to obtain forwarded port"}


@router.post("/health")
async def check_vpn_health(user: User = Depends(require_admin)):
    healthy = await vpn_engine.health_check()
    return {"healthy": healthy, "status": vpn_engine.get_status().model_dump()}
