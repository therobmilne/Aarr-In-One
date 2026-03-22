from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.permissions import require_admin, require_power_user
from backend.database import get_db
from backend.models.download import DownloadStatus
from backend.models.user import User
from backend.modules.downloads import service
from backend.modules.downloads.schemas import DownloadCreate, DownloadResponse, DownloadStats

router = APIRouter(prefix="/downloads", tags=["downloads"])


@router.get("", response_model=list[DownloadResponse])
async def list_downloads(
    status: DownloadStatus | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    downloads = await service.list_downloads(db, status, limit)
    return [DownloadResponse.model_validate(d) for d in downloads]


@router.post("", response_model=DownloadResponse, status_code=201)
async def add_download(
    body: DownloadCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    dl = await service.add_download(body, db)
    return DownloadResponse.model_validate(dl)


@router.get("/stats", response_model=DownloadStats)
async def download_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    return await service.get_stats(db)


@router.post("/{download_id}/pause", response_model=DownloadResponse)
async def pause_download(
    download_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    dl = await service.pause_download(download_id, db)
    return DownloadResponse.model_validate(dl)


@router.post("/{download_id}/resume", response_model=DownloadResponse)
async def resume_download(
    download_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    dl = await service.resume_download(download_id, db)
    return DownloadResponse.model_validate(dl)


@router.delete("/{download_id}")
async def delete_download(
    download_id: int,
    delete_files: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    await service.delete_download(download_id, db, delete_files)
    return {"status": "deleted"}
