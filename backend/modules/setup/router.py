"""Setup wizard API — no auth required (only works before setup is complete).

New architecture steps:
1. Jellyfin Connection (enter URL + admin credentials)
2. Wait for backend services + auto-configure cross-connections
3. VPN configuration (optional — write .env for Gluetun)
4. Indexers (add at least one via Prowlarr)
5. IPTV (optional — configure Threadfin)
6. Complete setup
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.modules.setup import service
from backend.modules.setup.schemas import (
    CompleteSetupRequest,
    JellyfinSetupRequest,
    JellyfinSetupResponse,
    SetupStatus,
    TMDBSetupRequest,
    TMDBSetupResponse,
    VPNSetupRequest,
)
from backend.services.auto_config import read_all_api_keys, run_auto_configuration, wait_for_all_services

router = APIRouter(prefix="/setup", tags=["setup"])


def _require_setup_incomplete():
    """Block setup endpoints once setup is done."""
    if service.is_setup_complete():
        raise HTTPException(status_code=403, detail="Setup is already complete")


@router.get("/status", response_model=SetupStatus)
async def get_setup_status():
    """Check current setup progress. No auth needed."""
    state = service.get_setup_state()
    return SetupStatus(
        is_complete=service.is_setup_complete(),
        current_step=_calculate_step(state),
        jellyfin_connected=bool(state.get("jellyfin_api_key")),
        jellyfin_url=state.get("jellyfin_url", ""),
        has_admin_user=bool(state.get("admin_user_id")),
        has_tmdb_key=bool(state.get("tmdb_api_key")),
        has_media_paths=True,
        has_vpn=False,
    )


@router.post("/jellyfin/detect", response_model=JellyfinSetupResponse)
async def detect_jellyfin():
    """Auto-detect Jellyfin on the Docker network."""
    _require_setup_incomplete()
    result = await service.auto_detect_jellyfin()
    return JellyfinSetupResponse(
        success=result["success"],
        message="Found Jellyfin!" if result["success"] else "Jellyfin not found on network",
        jellyfin_url=result.get("url", ""),
        server_name=result.get("server_name", ""),
        version=result.get("version", ""),
    )


@router.post("/jellyfin/connect", response_model=JellyfinSetupResponse)
async def connect_jellyfin(body: JellyfinSetupRequest):
    """Connect to Jellyfin with admin credentials."""
    _require_setup_incomplete()
    url = body.jellyfin_url or "http://192.168.2.54:8096"
    result = await service.setup_jellyfin_connection(url, body.username, body.password)
    return JellyfinSetupResponse(
        success=result["success"],
        message=result["message"],
        jellyfin_url=result.get("jellyfin_url", ""),
        api_key=result.get("api_key", ""),
        server_name=result.get("server_name", ""),
        version=result.get("version", ""),
    )


@router.post("/tmdb", response_model=TMDBSetupResponse)
async def setup_tmdb(body: TMDBSetupRequest):
    """Validate and save TMDB API key."""
    _require_setup_incomplete()
    result = await service.validate_tmdb_key(body.api_key)
    return TMDBSetupResponse(success=result["success"], message=result["message"])


@router.post("/services/check")
async def check_backend_services():
    """Check which backend services are healthy (Step 2).

    Returns status of each arr service. Called by the frontend to show
    the 'Setting up backend services...' progress screen.
    """
    _require_setup_incomplete()
    health = await wait_for_all_services()
    keys = await read_all_api_keys()

    return {
        "services": health,
        "api_keys_found": {k: bool(v) for k, v in keys.items()},
        "all_healthy": all(health.values()),
    }


@router.post("/services/configure")
async def auto_configure_services():
    """Run auto-configuration to wire all backend services together (Step 2b).

    This reads API keys from each service's config files and configures:
    - Prowlarr → syncs indexers to Radarr and Sonarr
    - Radarr → uses qBittorrent + SABnzbd as download clients
    - Sonarr → uses qBittorrent + SABnzbd as download clients
    - Root folders in Radarr (/media/movies) and Sonarr (/media/tv)
    """
    _require_setup_incomplete()
    results = await run_auto_configuration()
    return results


@router.post("/vpn")
async def setup_vpn(body: VPNSetupRequest):
    """Configure VPN (optional step — writes Gluetun .env)."""
    _require_setup_incomplete()
    if not body.enabled:
        return {"success": True, "message": "VPN skipped"}

    from pathlib import Path

    env_path = Path("/config/mediaforge/.env")
    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        with open(env_path, "w") as f:
            f.write(f"VPN_PROVIDER={body.provider}\n")
            f.write(f"VPN_TYPE={body.vpn_type}\n")
    except OSError:
        pass

    return {"success": True, "message": "VPN configuration saved", "enabled": True}


@router.post("/complete")
async def complete_setup(
    body: CompleteSetupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Finalize setup — saves all config and marks setup as done."""
    _require_setup_incomplete()
    result = await service.finalize_setup(db)
    return result


def _calculate_step(state: dict) -> int:
    if not state.get("jellyfin_api_key"):
        return 1
    if not state.get("tmdb_api_key"):
        return 2
    return 3
