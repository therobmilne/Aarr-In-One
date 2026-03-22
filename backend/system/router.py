"""System API — health checks and service status."""

from typing import Any

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.middleware import get_current_user
from backend.auth.permissions import require_admin
from backend.config import settings
from backend.database import get_db
from backend.logging_config import get_logger
from backend.models.user import User
from backend.services import settings_service
from backend.services.file_manager import check_disk_space
from backend.system.schemas import DiskInfo, HealthResponse, SystemInfo
from backend.websocket_manager import manager

logger = get_logger("system")

router = APIRouter(prefix="/system", tags=["system"])

# Backend service URLs to health-check
_SERVICE_CHECKS = {
    "radarr": f"{settings.RADARR_URL}/api/v3/system/status",
    "sonarr": f"{settings.SONARR_URL}/api/v3/system/status",
    "prowlarr": f"{settings.PROWLARR_URL}/api/v1/system/status",
    "qbittorrent": f"{settings.QBITTORRENT_URL}/api/v2/app/version",
    "bazarr": f"{settings.BAZARR_URL}/api/system/status",
    "gluetun": f"{settings.GLUETUN_URL}/v1/publicip/ip",
    "threadfin": f"{settings.THREADFIN_URL}/api/",
}


@router.get("/health")
async def health_check():
    """Health check — probes all backend services."""
    services = {}
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in _SERVICE_CHECKS.items():
            try:
                resp = await client.get(url)
                services[name] = {
                    "status": "healthy" if resp.status_code < 400 else "degraded",
                    "code": resp.status_code,
                }
            except Exception:
                services[name] = {"status": "unreachable", "code": 0}

    # Overall status
    statuses = [s["status"] for s in services.values()]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "unreachable" for s in statuses):
        overall = "degraded"
    else:
        overall = "unhealthy"

    return {"status": overall, "services": services}


@router.get("/info", response_model=SystemInfo)
async def system_info(user: User = Depends(require_admin)):
    disks = []
    for path_name, path_val in [
        ("config", settings.CONFIG_DIR),
        ("downloads", settings.DOWNLOAD_DIR),
        ("media", settings.MEDIA_DIR),
    ]:
        try:
            info = check_disk_space(path_val)
            disks.append(DiskInfo(path=path_val, **info))
        except Exception:
            pass

    return SystemInfo(
        disk=disks,
        websocket_connections=manager.connection_count,
    )


@router.get("/services")
async def service_status(user: User = Depends(require_admin)):
    """Detailed status of all backend arr services."""
    results = {}
    async with httpx.AsyncClient(timeout=5) as client:
        for name, url in _SERVICE_CHECKS.items():
            try:
                resp = await client.get(url)
                results[name] = {
                    "healthy": resp.status_code < 400,
                    "status_code": resp.status_code,
                    "url": url,
                }
                # Try to extract version info
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, dict) and "version" in data:
                            results[name]["version"] = data["version"]
                    except Exception:
                        pass
            except Exception as e:
                results[name] = {
                    "healthy": False,
                    "status_code": 0,
                    "url": url,
                    "error": str(e),
                }
    return results


@router.get("/settings")
async def get_settings(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict[str, Any]:
    return await settings_service.get_all_settings(db, category)


@router.put("/settings")
async def update_settings(
    updates: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    for key, value in updates.items():
        await settings_service.set_setting(db, key, value)
    return {"status": "ok", "updated": len(updates)}
