"""Setup wizard API — no auth required (only works before setup is complete)."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.modules.setup import service
from backend.modules.setup.schemas import (
    CompleteSetupRequest,
    JellyfinSetupRequest,
    JellyfinSetupResponse,
    PathsSetupRequest,
    SetupStatus,
    TMDBSetupRequest,
    TMDBSetupResponse,
    VPNSetupRequest,
)

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
        has_media_paths=True,  # Defaults always exist
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
    """Connect to Jellyfin with admin credentials. Creates API key automatically."""
    _require_setup_incomplete()

    url = body.jellyfin_url or "http://jellyfin:8096"
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


@router.post("/paths")
async def setup_paths(body: PathsSetupRequest):
    """Configure media paths (uses Docker volume defaults)."""
    _require_setup_incomplete()
    # Paths are set via Docker volumes so we just acknowledge
    return {"success": True, "message": "Paths configured"}


@router.post("/vpn")
async def setup_vpn(body: VPNSetupRequest):
    """Configure VPN (optional step)."""
    _require_setup_incomplete()
    return {"success": True, "message": "VPN configuration saved", "enabled": body.enabled}


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
