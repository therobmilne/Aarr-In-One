import asyncio

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.permissions import require_admin, require_power_user
from backend.database import get_db
from backend.models.user import User
from backend.modules.livetv import service
from backend.modules.livetv.schemas import (
    ChannelResponse,
    ChannelUpdate,
    EPGEntryResponse,
    PlaylistCreate,
    PlaylistResponse,
    RecordingCreate,
    RecordingResponse,
)

router = APIRouter(prefix="/livetv", tags=["livetv"])


# --- Playlists ---

@router.get("/playlists", response_model=list[PlaylistResponse])
async def list_playlists(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    playlists = await service.list_playlists(db)
    return [PlaylistResponse.model_validate(p) for p in playlists]


@router.post("/playlists", response_model=PlaylistResponse, status_code=201)
async def import_playlist(
    body: PlaylistCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    playlist = await service.import_playlist(body, db)
    return PlaylistResponse.model_validate(playlist)


@router.post("/playlists/{playlist_id}/refresh")
async def refresh_playlist(
    playlist_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    count = await service.refresh_playlist(playlist_id, db)
    return {"status": "refreshed", "channels": count}


# --- Channels ---

@router.get("/channels", response_model=list[ChannelResponse])
async def list_channels(
    playlist_id: int | None = None,
    enabled: bool | None = None,
    group: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    channels = await service.list_channels(db, playlist_id, enabled, group)
    return [ChannelResponse.model_validate(c) for c in channels]


@router.put("/channels/{channel_id}", response_model=ChannelResponse)
async def update_channel(
    channel_id: int,
    body: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    ch = await service.update_channel(channel_id, body, db)
    return ChannelResponse.model_validate(ch)


# --- M3U / XMLTV Output ---

@router.get("/output/m3u")
async def m3u_output(db: AsyncSession = Depends(get_db)):
    """Serve clean M3U for Jellyfin."""
    channels = await service.list_channels(db, enabled=True)
    content = service.generate_m3u_output(channels)
    return PlainTextResponse(content, media_type="audio/x-mpegurl")


# --- EPG ---

@router.get("/epg", response_model=list[EPGEntryResponse])
async def get_epg(
    channel_epg_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    entries = await service.get_epg(db, channel_epg_id)
    return [EPGEntryResponse.model_validate(e) for e in entries]


# --- Recordings ---

@router.get("/recordings", response_model=list[RecordingResponse])
async def list_recordings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    recordings = await service.list_recordings(db)
    return [RecordingResponse.model_validate(r) for r in recordings]


@router.post("/recordings", response_model=RecordingResponse, status_code=201)
async def create_recording(
    body: RecordingCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    rec = await service.create_recording(body, db)
    return RecordingResponse.model_validate(rec)


# --- Stream Proxy ---

@router.get("/stream/{channel_id}")
async def stream_channel(channel_id: int, request: Request):
    """Proxy an IPTV stream — zero-copy byte forwarding."""
    from backend.database import async_session
    from backend.models.livetv import IPTVChannel
    from sqlalchemy import select

    async with async_session() as db:
        result = await db.execute(select(IPTVChannel).where(IPTVChannel.id == channel_id))
        channel = result.scalar_one_or_none()

    if not channel:
        return PlainTextResponse("Channel not found", status_code=404)

    import httpx

    async def stream_generator():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", channel.stream_url) as resp:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk

    return StreamingResponse(
        stream_generator(),
        media_type="video/mp2t",
        headers={"Cache-Control": "no-cache"},
    )
