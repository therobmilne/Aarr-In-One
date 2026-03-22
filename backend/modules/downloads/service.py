from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.exceptions import NotFoundError
from backend.logging_config import get_logger
from backend.models.download import Download, DownloadStatus, DownloadType
from backend.models.download import DownloadCategory
from backend.modules.downloads.release_parser import detect_category
from backend.modules.downloads.schemas import DownloadCreate, DownloadStats
from backend.modules.downloads.torrent_client import torrent_client
from backend.modules.downloads.usenet_client import usenet_client
from backend.websocket_manager import manager

logger = get_logger("downloads")


async def add_download(data: DownloadCreate, db: AsyncSession) -> Download:
    # Auto-detect category from release name if not specified
    category = data.category
    if category == DownloadCategory.OTHER:
        detected = detect_category(data.title)
        category = DownloadCategory.MOVIES if detected == "movies" else DownloadCategory.TV

    download = Download(
        type=data.type,
        title=data.title,
        download_url=data.download_url,
        category=category,
        movie_id=data.movie_id,
        episode_id=data.episode_id,
        status=DownloadStatus.QUEUED,
    )
    db.add(download)
    await db.flush()

    # Start the actual download
    try:
        if data.type == DownloadType.TORRENT:
            info_hash = await torrent_client.add_torrent(data.download_url)
            download.info_hash = info_hash
            download.status = DownloadStatus.DOWNLOADING
        elif data.type == DownloadType.USENET:
            nzb_id = await usenet_client.add_nzb_url(data.download_url, data.title, data.category.value)
            download.info_hash = nzb_id
            download.status = DownloadStatus.DOWNLOADING
    except Exception as e:
        download.status = DownloadStatus.FAILED
        download.error_message = str(e)
        logger.error("download_start_failed", title=data.title, error=str(e))

    await db.flush()
    await manager.broadcast("download:started", {"id": download.id, "title": data.title})
    return download


async def list_downloads(
    db: AsyncSession,
    status: DownloadStatus | None = None,
    limit: int = 50,
) -> list[Download]:
    query = select(Download).order_by(Download.created_at.desc())
    if status:
        query = query.where(Download.status == status)
    query = query.limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_download(download_id: int, db: AsyncSession) -> Download:
    result = await db.execute(select(Download).where(Download.id == download_id))
    dl = result.scalar_one_or_none()
    if not dl:
        raise NotFoundError("Download", download_id)
    return dl


async def pause_download(download_id: int, db: AsyncSession) -> Download:
    dl = await get_download(download_id, db)
    if dl.type == DownloadType.TORRENT and dl.info_hash:
        torrent_client.pause(dl.info_hash)
    elif dl.type == DownloadType.USENET and dl.info_hash:
        usenet_client.pause(dl.info_hash)
    dl.status = DownloadStatus.PAUSED
    return dl


async def resume_download(download_id: int, db: AsyncSession) -> Download:
    dl = await get_download(download_id, db)
    if dl.type == DownloadType.TORRENT and dl.info_hash:
        torrent_client.resume(dl.info_hash)
    elif dl.type == DownloadType.USENET and dl.info_hash:
        usenet_client.resume(dl.info_hash)
    dl.status = DownloadStatus.DOWNLOADING
    return dl


async def delete_download(download_id: int, db: AsyncSession, delete_files: bool = False) -> None:
    dl = await get_download(download_id, db)
    if dl.type == DownloadType.TORRENT and dl.info_hash:
        torrent_client.remove(dl.info_hash, delete_files)
    elif dl.type == DownloadType.USENET and dl.info_hash:
        usenet_client.remove(dl.info_hash)
    await db.delete(dl)


async def get_stats(db: AsyncSession) -> DownloadStats:
    active_statuses = [DownloadStatus.DOWNLOADING, DownloadStatus.SEEDING]
    result = await db.execute(
        select(
            func.count(Download.id),
            func.coalesce(func.sum(Download.speed_bytes_sec), 0),
            func.coalesce(func.sum(Download.downloaded_bytes), 0),
            func.coalesce(func.sum(Download.size_bytes), 0),
        ).where(Download.status.in_(active_statuses))
    )
    row = result.one()
    return DownloadStats(
        active_count=row[0],
        total_speed_bytes_sec=row[1],
        total_downloaded_bytes=row[2],
        total_size_bytes=row[3],
    )
