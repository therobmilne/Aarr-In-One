from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, AsyncGenerator
from xml.etree import ElementTree

import httpx

from backend.logging_config import get_logger
from backend.modules.iptv.xtream_client import XtreamClient

logger = get_logger("iptv.scanner")

# Characters that are not allowed in file/directory names
_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe_name(name: str) -> str:
    """Sanitise a string so it is safe to use as a file or directory name."""
    name = _INVALID_CHARS.sub("", name).strip(". ")
    return name or "Unknown"


async def scan_vod_movies(
    client: XtreamClient,
    output_dir: str = "/media/iptv-movies",
) -> AsyncGenerator[dict[str, Any], None]:
    """Scan the provider for VOD movies and create ``.strm`` files.

    Yields progress dicts suitable for WebSocket updates.
    """
    start = time.monotonic()
    phase = "movies"

    yield {"phase": phase, "found": 0, "processed": 0, "total": 0, "skipped": 0,
           "is_complete": False, "elapsed_seconds": 0.0}

    try:
        movies = await client.get_vod_movies()
    except Exception as exc:
        logger.error("scan_movies_fetch_failed", error=str(exc))
        yield {"phase": phase, "found": 0, "processed": 0, "total": 0, "skipped": 0,
               "is_complete": True, "elapsed_seconds": time.monotonic() - start}
        return

    total = len(movies)
    processed = 0
    skipped = 0
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    yield {"phase": phase, "found": total, "processed": 0, "total": total, "skipped": 0,
           "is_complete": False, "elapsed_seconds": time.monotonic() - start}

    for movie in movies:
        name = movie.get("name") or movie.get("title") or "Unknown"
        stream_id = movie.get("stream_id")
        extension = movie.get("container_extension") or "mp4"

        if not stream_id:
            skipped += 1
            processed += 1
            continue

        safe = _safe_name(name)
        movie_dir = out / safe
        strm_path = movie_dir / f"{safe}.strm"

        if strm_path.exists():
            skipped += 1
            processed += 1
            # Emit progress every 200 items to avoid flooding
            if processed % 200 == 0:
                yield {"phase": phase, "found": total, "processed": processed,
                       "total": total, "skipped": skipped, "is_complete": False,
                       "elapsed_seconds": time.monotonic() - start}
            continue

        url = client.generate_stream_url(stream_id, stream_type="movie", container_extension=extension)

        try:
            movie_dir.mkdir(parents=True, exist_ok=True)
            strm_path.write_text(url, encoding="utf-8")
        except OSError as exc:
            logger.warning("strm_write_failed", path=str(strm_path), error=str(exc))
            skipped += 1

        processed += 1
        if processed % 200 == 0:
            yield {"phase": phase, "found": total, "processed": processed,
                   "total": total, "skipped": skipped, "is_complete": False,
                   "elapsed_seconds": time.monotonic() - start}

    yield {"phase": phase, "found": total, "processed": processed,
           "total": total, "skipped": skipped, "is_complete": True,
           "elapsed_seconds": time.monotonic() - start}


async def scan_vod_series(
    client: XtreamClient,
    output_dir: str = "/media/iptv-shows",
) -> AsyncGenerator[dict[str, Any], None]:
    """Scan the provider for VOD series and create ``.strm`` files.

    Files are organised as ``<output_dir>/<show>/<Season XX>/<show> - SXXEXX.strm``.
    Yields progress dicts.
    """
    start = time.monotonic()
    phase = "series"

    yield {"phase": phase, "found": 0, "processed": 0, "total": 0, "skipped": 0,
           "is_complete": False, "elapsed_seconds": 0.0}

    try:
        series_list = await client.get_vod_series()
    except Exception as exc:
        logger.error("scan_series_fetch_failed", error=str(exc))
        yield {"phase": phase, "found": 0, "processed": 0, "total": 0, "skipped": 0,
               "is_complete": True, "elapsed_seconds": time.monotonic() - start}
        return

    total = len(series_list)
    processed = 0
    skipped = 0
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    yield {"phase": phase, "found": total, "processed": 0, "total": total, "skipped": 0,
           "is_complete": False, "elapsed_seconds": time.monotonic() - start}

    for series in series_list:
        series_name = series.get("name") or series.get("title") or "Unknown"
        series_id = series.get("series_id")

        if not series_id:
            skipped += 1
            processed += 1
            continue

        safe_show = _safe_name(series_name)
        show_dir = out / safe_show

        # The Xtream API doesn't always provide episode-level data in
        # get_series.  Many providers only give series metadata at this
        # endpoint.  We still create the folder structure and a single
        # strm pointing at the series stream so it is picked up by
        # Jellyfin.  Providers that expose full season/episode info via
        # ``get_series_info`` can be handled in a future enhancement; for
        # now we generate one strm per series entry which will play the
        # first available episode.

        # Try to extract seasons/episodes from inline data if present
        episodes_data: list[dict] = series.get("episodes", [])

        if episodes_data and isinstance(episodes_data, dict):
            # Some providers return episodes as {season_num: [episodes]}
            for season_num, eps in episodes_data.items():
                season_label = f"Season {int(season_num):02d}"
                season_dir = show_dir / season_label
                for ep in eps:
                    ep_num = ep.get("episode_num", 1)
                    ep_id = ep.get("id") or ep.get("stream_id")
                    ext = ep.get("container_extension") or "mp4"
                    if not ep_id:
                        skipped += 1
                        continue
                    ep_name = f"{safe_show} - S{int(season_num):02d}E{int(ep_num):02d}.strm"
                    strm_path = season_dir / ep_name
                    if strm_path.exists():
                        skipped += 1
                        continue
                    url = client.generate_stream_url(ep_id, stream_type="series", container_extension=ext)
                    try:
                        season_dir.mkdir(parents=True, exist_ok=True)
                        strm_path.write_text(url, encoding="utf-8")
                    except OSError as exc:
                        logger.warning("strm_write_failed", path=str(strm_path), error=str(exc))
                        skipped += 1
        else:
            # Fallback: create a simple strm for the series itself
            season_dir = show_dir / "Season 01"
            strm_path = season_dir / f"{safe_show} - S01E01.strm"
            if strm_path.exists():
                skipped += 1
            else:
                url = client.generate_stream_url(series_id, stream_type="series", container_extension="mp4")
                try:
                    season_dir.mkdir(parents=True, exist_ok=True)
                    strm_path.write_text(url, encoding="utf-8")
                except OSError as exc:
                    logger.warning("strm_write_failed", path=str(strm_path), error=str(exc))
                    skipped += 1

        processed += 1
        if processed % 100 == 0:
            yield {"phase": phase, "found": total, "processed": processed,
                   "total": total, "skipped": skipped, "is_complete": False,
                   "elapsed_seconds": time.monotonic() - start}

    yield {"phase": phase, "found": total, "processed": processed,
           "total": total, "skipped": skipped, "is_complete": True,
           "elapsed_seconds": time.monotonic() - start}


async def scan_live_channels(
    client: XtreamClient,
) -> AsyncGenerator[dict[str, Any], None]:
    """Scan live channels and yield progress.

    Channel data is returned in the final progress dict under the ``channels``
    key so the caller can persist it to the database.
    """
    start = time.monotonic()
    phase = "live"

    yield {"phase": phase, "found": 0, "processed": 0, "total": 0, "skipped": 0,
           "is_complete": False, "elapsed_seconds": 0.0}

    try:
        channels = await client.get_live_channels()
    except Exception as exc:
        logger.error("scan_live_fetch_failed", error=str(exc))
        yield {"phase": phase, "found": 0, "processed": 0, "total": 0, "skipped": 0,
               "is_complete": True, "elapsed_seconds": time.monotonic() - start}
        return

    try:
        categories = await client.get_live_categories()
    except Exception:
        categories = []

    cat_map: dict[str, str] = {}
    for cat in categories:
        cat_id = str(cat.get("category_id", ""))
        cat_name = cat.get("category_name", "")
        if cat_id:
            cat_map[cat_id] = cat_name

    total = len(channels)
    processed = 0
    skipped = 0
    channel_records: list[dict[str, Any]] = []

    yield {"phase": phase, "found": total, "processed": 0, "total": total, "skipped": 0,
           "is_complete": False, "elapsed_seconds": time.monotonic() - start}

    for ch in channels:
        stream_id = ch.get("stream_id")
        if not stream_id:
            skipped += 1
            processed += 1
            continue

        name = ch.get("name") or "Unknown"
        cat_id = str(ch.get("category_id", ""))
        category_name = cat_map.get(cat_id, "")
        logo = ch.get("stream_icon") or ""
        epg_id = ch.get("epg_channel_id") or ""

        stream_url = client.generate_stream_url(stream_id, stream_type="live")

        channel_records.append({
            "stream_id": stream_id,
            "name": name,
            "category": category_name,
            "logo_url": logo,
            "epg_id": epg_id,
            "stream_url": stream_url,
        })

        processed += 1
        if processed % 500 == 0:
            yield {"phase": phase, "found": total, "processed": processed,
                   "total": total, "skipped": skipped, "is_complete": False,
                   "elapsed_seconds": time.monotonic() - start}

    yield {"phase": phase, "found": total, "processed": processed,
           "total": total, "skipped": skipped, "is_complete": True,
           "elapsed_seconds": time.monotonic() - start,
           "channels": channel_records}


async def fetch_epg(
    client: XtreamClient,
) -> AsyncGenerator[dict[str, Any], None]:
    """Download the XMLTV EPG from the Xtream provider and return parsed entries.

    Fetches: {server_url}/xmltv.php?username={user}&password={pass}

    Yields progress dicts.  The final dict contains an ``epg_entries`` key with
    the list of parsed programme dicts ready for database insertion.
    """
    start = time.monotonic()
    phase = "epg"

    yield {"phase": phase, "found": 0, "processed": 0, "total": 0, "skipped": 0,
           "is_complete": False, "elapsed_seconds": 0.0}

    epg_url = client.get_epg_url()
    entries: list[dict[str, Any]] = []

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=15.0),
            follow_redirects=True,
        ) as http:
            resp = await http.get(epg_url)
            resp.raise_for_status()

        root = ElementTree.fromstring(resp.content)
        programmes = root.findall(".//programme")
        total = len(programmes)

        yield {"phase": phase, "found": total, "processed": 0, "total": total,
               "skipped": 0, "is_complete": False,
               "elapsed_seconds": time.monotonic() - start}

        for idx, prog in enumerate(programmes, 1):
            channel_epg_id = prog.get("channel", "")
            title = prog.findtext("title", "")
            if not channel_epg_id or not title:
                continue

            icon_el = prog.find("icon")
            entries.append({
                "channel_epg_id": channel_epg_id,
                "title": title,
                "description": prog.findtext("desc", ""),
                "start_time": prog.get("start", ""),
                "end_time": prog.get("stop", ""),
                "category": prog.findtext("category", ""),
                "icon_url": icon_el.get("src", "") if icon_el is not None else "",
            })

            if idx % 2000 == 0:
                yield {"phase": phase, "found": total, "processed": idx, "total": total,
                       "skipped": 0, "is_complete": False,
                       "elapsed_seconds": time.monotonic() - start}

        logger.info("epg_fetched", programmes=total, parsed=len(entries))

    except Exception as exc:
        logger.error("epg_fetch_failed", error=str(exc))

    yield {"phase": phase, "found": len(entries), "processed": len(entries),
           "total": len(entries), "skipped": 0, "is_complete": True,
           "elapsed_seconds": time.monotonic() - start,
           "epg_entries": entries}
