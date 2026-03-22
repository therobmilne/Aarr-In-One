"""Live TV service: M3U parsing, EPG handling, channel management."""

import re
from io import StringIO

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.exceptions import NotFoundError
from backend.logging_config import get_logger
from backend.models.livetv import DVRRecording, EPGEntry, IPTVChannel, IPTVPlaylist
from backend.modules.livetv.schemas import ChannelUpdate, PlaylistCreate, RecordingCreate

logger = get_logger("livetv")


def parse_m3u(content: str, playlist_id: int) -> list[IPTVChannel]:
    """Parse M3U playlist content into channel objects."""
    channels = []
    lines = content.strip().split("\n")
    i = 0
    channel_num = 1

    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF:"):
            # Parse attributes
            attrs = {}
            attr_pattern = r'(\w[\w-]*)="([^"]*)"'
            for match in re.finditer(attr_pattern, line):
                attrs[match.group(1).lower()] = match.group(2)

            # Title is after the last comma
            title = line.rsplit(",", 1)[-1].strip() if "," in line else ""

            # Get stream URL (next non-comment line)
            i += 1
            while i < len(lines) and lines[i].strip().startswith("#"):
                i += 1
            if i < len(lines):
                stream_url = lines[i].strip()
                if stream_url and not stream_url.startswith("#"):
                    channels.append(IPTVChannel(
                        playlist_id=playlist_id,
                        name=title or attrs.get("tvg-name", f"Channel {channel_num}"),
                        channel_number=int(attrs["tvg-chno"]) if "tvg-chno" in attrs else channel_num,
                        group=attrs.get("group-title", ""),
                        logo_url=attrs.get("tvg-logo", ""),
                        stream_url=stream_url,
                        epg_id=attrs.get("tvg-id", ""),
                        enabled=True,
                        category=attrs.get("group-title", ""),
                    ))
                    channel_num += 1
        i += 1

    return channels


async def import_playlist(data: PlaylistCreate, db: AsyncSession) -> IPTVPlaylist:
    """Import an M3U playlist from URL."""
    playlist = IPTVPlaylist(
        name=data.name,
        url=data.url,
        enabled=data.enabled,
        auto_refresh=data.auto_refresh,
        refresh_interval_hours=data.refresh_interval_hours,
    )
    db.add(playlist)
    await db.flush()

    # Download and parse M3U
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.get(data.url)
        resp.raise_for_status()
        content = resp.text

    channels = parse_m3u(content, playlist.id)
    for ch in channels:
        db.add(ch)

    playlist.channel_count = len(channels)
    await db.flush()

    logger.info("playlist_imported", name=data.name, channels=len(channels))
    return playlist


async def refresh_playlist(playlist_id: int, db: AsyncSession) -> int:
    """Re-download and re-parse a playlist."""
    result = await db.execute(select(IPTVPlaylist).where(IPTVPlaylist.id == playlist_id))
    playlist = result.scalar_one_or_none()
    if not playlist:
        raise NotFoundError("Playlist", playlist_id)

    # Remove old channels
    await db.execute(delete(IPTVChannel).where(IPTVChannel.playlist_id == playlist_id))

    # Re-import
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.get(playlist.url)
        resp.raise_for_status()

    channels = parse_m3u(resp.text, playlist.id)
    for ch in channels:
        db.add(ch)

    playlist.channel_count = len(channels)
    await db.flush()
    return len(channels)


async def list_playlists(db: AsyncSession) -> list[IPTVPlaylist]:
    result = await db.execute(select(IPTVPlaylist).order_by(IPTVPlaylist.name))
    return list(result.scalars().all())


async def list_channels(
    db: AsyncSession,
    playlist_id: int | None = None,
    enabled: bool | None = None,
    group: str | None = None,
) -> list[IPTVChannel]:
    query = select(IPTVChannel).order_by(IPTVChannel.channel_number)
    if playlist_id:
        query = query.where(IPTVChannel.playlist_id == playlist_id)
    if enabled is not None:
        query = query.where(IPTVChannel.enabled == enabled)
    if group:
        query = query.where(IPTVChannel.group == group)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_channel(channel_id: int, data: ChannelUpdate, db: AsyncSession) -> IPTVChannel:
    result = await db.execute(select(IPTVChannel).where(IPTVChannel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise NotFoundError("Channel", channel_id)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(channel, field, value)
    await db.flush()
    return channel


async def get_epg(db: AsyncSession, channel_epg_id: str | None = None) -> list[EPGEntry]:
    query = select(EPGEntry)
    if channel_epg_id:
        query = query.where(EPGEntry.channel_epg_id == channel_epg_id)
    query = query.order_by(EPGEntry.start_time).limit(500)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_recording(data: RecordingCreate, db: AsyncSession) -> DVRRecording:
    recording = DVRRecording(
        channel_id=data.channel_id,
        title=data.title,
        start_time=data.start_time,
        end_time=data.end_time,
        is_series_rule=data.is_series_rule,
        series_rule_pattern=data.series_rule_pattern,
    )
    db.add(recording)
    await db.flush()
    return recording


async def list_recordings(db: AsyncSession) -> list[DVRRecording]:
    result = await db.execute(select(DVRRecording).order_by(DVRRecording.start_time.desc()))
    return list(result.scalars().all())


def generate_m3u_output(channels: list[IPTVChannel]) -> str:
    """Generate clean M3U output for Jellyfin."""
    lines = ["#EXTM3U"]
    for ch in channels:
        if not ch.enabled:
            continue
        attrs = []
        if ch.channel_number:
            attrs.append(f'tvg-chno="{ch.channel_number}"')
        if ch.epg_id:
            attrs.append(f'tvg-id="{ch.epg_id}"')
        if ch.logo_url:
            attrs.append(f'tvg-logo="{ch.logo_url}"')
        if ch.group:
            attrs.append(f'group-title="{ch.group}"')
        attr_str = " ".join(attrs)
        lines.append(f'#EXTINF:-1 {attr_str},{ch.name}')
        lines.append(ch.stream_url)
    return "\n".join(lines)


def generate_xmltv_output(channels: list[IPTVChannel], epg_entries: list[EPGEntry]) -> str:
    """Generate XMLTV XML output for Jellyfin EPG."""
    from xml.etree.ElementTree import Element, SubElement, tostring

    tv = Element("tv", attrib={"generator-info-name": "MediaForge"})

    # Channel definitions
    for ch in channels:
        if not ch.enabled or not ch.epg_id:
            continue
        chan_el = SubElement(tv, "channel", id=ch.epg_id)
        dn = SubElement(chan_el, "display-name")
        dn.text = ch.name
        if ch.logo_url:
            SubElement(chan_el, "icon", src=ch.logo_url)

    # Programme entries
    for entry in epg_entries:
        prog = SubElement(
            tv, "programme",
            start=entry.start_time,
            stop=entry.end_time,
            channel=entry.channel_epg_id,
        )
        title_el = SubElement(prog, "title")
        title_el.text = entry.title
        if entry.description:
            desc_el = SubElement(prog, "desc")
            desc_el.text = entry.description
        if entry.category:
            cat_el = SubElement(prog, "category")
            cat_el.text = entry.category
        if entry.icon_url:
            SubElement(prog, "icon", src=entry.icon_url)

    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tostring(tv, encoding="unicode")
