from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.middleware import get_current_user
from backend.auth.permissions import require_admin
from backend.database import get_db
from backend.models.user import User
from backend.services import settings_service
from backend.services.file_manager import check_disk_space
from backend.system.health import get_all_health
from backend.system.schemas import DiskInfo, HealthResponse, SystemInfo
from backend.websocket_manager import manager

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=HealthResponse)
async def health_check():
    subsystems = await get_all_health()
    statuses = [s.status for s in subsystems]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "error" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"
    return HealthResponse(status=overall, subsystems=subsystems)


@router.get("/info", response_model=SystemInfo)
async def system_info(user: User = Depends(require_admin)):
    from backend.config import settings

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
