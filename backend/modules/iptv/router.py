from __future__ import annotations

import asyncio
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db, async_session
from backend.logging_config import get_logger
from backend.modules.iptv.schemas import IPTVCredentials, IPTVTestResult, ScanProgress
from backend.modules.iptv.xtream_client import XtreamClient
from backend.modules.iptv import scanner
from backend.services.settings_service import get_setting, set_setting
from backend.websocket_manager import manager

logger = get_logger("iptv.router")

router = APIRouter(prefix="/iptv", tags=["iptv"])

# In-memory state for the currently-running scan
_scan_task: asyncio.Task | None = None
_scan_progress: dict[str, Any] = {
    "phase": "idle",
    "found": 0,
    "processed": 0,
    "total": 0,
    "skipped": 0,
    "is_complete": True,
    "elapsed_seconds": 0.0,
}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

async def _get_credentials(db: AsyncSession) -> IPTVCredentials | None:
    server_url = await get_setting(db, "iptv_server_url")
    username = await get_setting(db, "iptv_username")
    password = await get_setting(db, "iptv_password")
    if not all([server_url, username, password]):
        return None
    return IPTVCredentials(server_url=server_url, username=username, password=password)


def _build_client(creds: IPTVCredentials) -> XtreamClient:
    return XtreamClient(
        server_url=creds.server_url,
        username=creds.username,
        password=creds.password,
    )


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/test", response_model=IPTVTestResult)
async def test_credentials(
    body: IPTVCredentials,
) -> IPTVTestResult:
    """Test IPTV credentials by authenticating and fetching counts."""
    client = _build_client(body)

    try:
        await client.test_connection()
    except ConnectionError as exc:
        return IPTVTestResult(success=False, message=str(exc))

    # Fetch counts in parallel
    vod_count = 0
    series_count = 0
    live_count = 0

    try:
        vod, series, live = await asyncio.gather(
            client.get_vod_movies(),
            client.get_vod_series(),
            client.get_live_channels(),
            return_exceptions=True,
        )
        if isinstance(vod, list):
            vod_count = len(vod)
        if isinstance(series, list):
            series_count = len(series)
        if isinstance(live, list):
            live_count = len(live)
    except Exception:
        pass

    return IPTVTestResult(
        success=True,
        message="Connection successful",
        vod_count=vod_count,
        series_count=series_count,
        live_count=live_count,
    )


@router.post("/scan")
async def start_scan(
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Start a background IPTV scan. Returns immediately."""
    global _scan_task

    if _scan_task is not None and not _scan_task.done():
        raise HTTPException(status_code=409, detail="A scan is already running")

    creds = await _get_credentials(db)
    if creds is None:
        raise HTTPException(status_code=400, detail="IPTV credentials not configured")

    client = _build_client(creds)
    _scan_task = asyncio.create_task(_run_scan(client))
    return {"status": "scan_started"}


@router.get("/scan/status", response_model=ScanProgress)
async def scan_status() -> ScanProgress:
    """Return the current scan progress."""
    return ScanProgress(**{k: v for k, v in _scan_progress.items() if k not in ("channels", "epg_entries")})


@router.get("/credentials")
async def get_credentials(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return saved IPTV credentials with the password masked."""
    creds = await _get_credentials(db)
    if creds is None:
        return {"configured": False}
    masked = creds.password[:2] + "*" * max(len(creds.password) - 2, 0) if creds.password else ""
    return {
        "configured": True,
        "server_url": creds.server_url,
        "username": creds.username,
        "password": masked,
    }


@router.put("/credentials")
async def save_credentials(
    body: IPTVCredentials,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Save IPTV credentials to the database."""
    await set_setting(db, "iptv_server_url", body.server_url, category="iptv")
    await set_setting(db, "iptv_username", body.username, category="iptv")
    await set_setting(db, "iptv_password", body.password, category="iptv")
    return {"status": "saved"}


# ------------------------------------------------------------------
# Background scan runner
# ------------------------------------------------------------------

async def _run_scan(client: XtreamClient) -> None:
    """Execute a full IPTV scan (movies, series, live) in the background."""
    global _scan_progress

    logger.info("iptv_scan_started")

    # -- Movies --
    async for progress in scanner.scan_vod_movies(client):
        _scan_progress = progress
        await _broadcast_progress(progress)

    # -- Series --
    async for progress in scanner.scan_vod_series(client):
        _scan_progress = progress
        await _broadcast_progress(progress)

    # -- Live channels --
    channel_records: list[dict] = []
    async for progress in scanner.scan_live_channels(client):
        _scan_progress = progress
        channels = progress.get("channels")
        if channels:
            channel_records = channels
        await _broadcast_progress(progress)

    # Persist live channels to the database
    if channel_records:
        await _persist_live_channels(channel_records)

    # -- EPG --
    epg_entries: list[dict] = []
    async for progress in scanner.fetch_epg(client):
        _scan_progress = progress
        entries = progress.get("epg_entries")
        if entries:
            epg_entries = entries
        await _broadcast_progress(progress)

    if epg_entries:
        await _persist_epg(epg_entries)

    # Register the Xtream EPG URL so the periodic refresh task can use it too
    await _register_epg_url(client.get_epg_url())

    _scan_progress = {
        "phase": "idle",
        "found": 0,
        "processed": 0,
        "total": 0,
        "skipped": 0,
        "is_complete": True,
        "elapsed_seconds": 0.0,
    }

    await manager.broadcast("iptv_scan_complete", {"status": "complete"})
    logger.info("iptv_scan_finished")


async def _broadcast_progress(progress: dict[str, Any]) -> None:
    """Push scan progress to all connected WebSocket clients."""
    safe = {k: v for k, v in progress.items() if k not in ("channels", "epg_entries")}
    try:
        await manager.broadcast("iptv_scan_progress", safe)
    except Exception:
        pass  # Don't let WS errors kill the scan


async def _persist_live_channels(channel_records: list[dict[str, Any]]) -> None:
    """Store scanned live channels in the database via the livetv model."""
    try:
        from backend.models.livetv import IPTVChannel, IPTVPlaylist
        from sqlalchemy import select

        async with async_session() as db:
            # Find or create a system playlist for the Xtream scan
            result = await db.execute(
                select(IPTVPlaylist).where(IPTVPlaylist.name == "Xtream IPTV")
            )
            playlist = result.scalar_one_or_none()
            if playlist is None:
                playlist = IPTVPlaylist(
                    name="Xtream IPTV",
                    url="xtream://scan",
                    enabled=True,
                    auto_refresh=False,
                    refresh_interval_hours=24,
                    channel_count=0,
                )
                db.add(playlist)
                await db.flush()

            # Upsert channels
            existing_result = await db.execute(
                select(IPTVChannel).where(IPTVChannel.playlist_id == playlist.id)
            )
            existing_map: dict[str, IPTVChannel] = {}
            for ch in existing_result.scalars().all():
                existing_map[ch.stream_url] = ch

            new_count = 0
            for rec in channel_records:
                url = rec["stream_url"]
                if url in existing_map:
                    # Update existing
                    existing = existing_map[url]
                    existing.name = rec["name"]
                    existing.category = rec.get("category")
                    existing.logo_url = rec.get("logo_url")
                    existing.epg_id = rec.get("epg_id")
                else:
                    ch = IPTVChannel(
                        playlist_id=playlist.id,
                        name=rec["name"],
                        stream_url=url,
                        group=rec.get("category"),
                        category=rec.get("category"),
                        logo_url=rec.get("logo_url"),
                        epg_id=rec.get("epg_id"),
                        enabled=True,
                    )
                    db.add(ch)
                    new_count += 1

            playlist.channel_count = len(channel_records)
            await db.commit()

            logger.info("live_channels_persisted", total=len(channel_records), new=new_count)
    except Exception as exc:
        logger.error("live_channels_persist_failed", error=str(exc))


async def _register_epg_url(epg_url: str) -> None:
    """Ensure the Xtream EPG URL is stored in the epg_urls setting list."""
    try:
        async with async_session() as db:
            existing = await get_setting(db, "epg_urls", [])
            if not isinstance(existing, list):
                existing = []
            if epg_url not in existing:
                existing.append(epg_url)
                await set_setting(db, "epg_urls", existing, category="iptv")
                await db.commit()
    except Exception as exc:
        logger.error("epg_url_register_failed", error=str(exc))


async def _persist_epg(epg_entries: list[dict[str, Any]]) -> None:
    """Store EPG entries fetched from the Xtream provider into the database.

    Replaces all existing EPG data with the freshly-fetched entries.
    """
    try:
        from sqlalchemy import delete

        from backend.models.livetv import EPGEntry

        async with async_session() as db:
            # Clear existing EPG data and replace with fresh entries
            await db.execute(delete(EPGEntry))

            for entry_data in epg_entries:
                entry = EPGEntry(
                    channel_epg_id=entry_data["channel_epg_id"],
                    title=entry_data["title"],
                    description=entry_data.get("description", ""),
                    start_time=entry_data["start_time"],
                    end_time=entry_data["end_time"],
                    category=entry_data.get("category", ""),
                    icon_url=entry_data.get("icon_url", ""),
                )
                db.add(entry)

            await db.commit()
            logger.info("epg_persisted", entries=len(epg_entries))
    except Exception as exc:
        logger.error("epg_persist_failed", error=str(exc))
