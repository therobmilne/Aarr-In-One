"""Media pipeline — orchestrates request → search → download → import.

Bridges the gap between a user requesting media and it appearing in the library.
When a request is approved, this module searches indexers, starts downloads,
and handles post-download importing into the media library.
"""

import asyncio
import json
import os
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.logging_config import get_logger
from backend.models.download import Download, DownloadCategory, DownloadStatus, DownloadType
from backend.models.media import Episode, MediaStatus, Movie, Season, Series
from backend.models.request import MediaRequest, RequestStatus, RequestType
from backend.modules.discovery.tmdb_client import tmdb_client
from backend.modules.downloads.release_parser import parse_release_name
from backend.modules.downloads.schemas import DownloadCreate
from backend.modules.downloads.service import add_download
from backend.modules.indexers.schemas import SearchResult
from backend.modules.indexers.service import search_all_indexers
from backend.services.file_manager import (
    MOVIE_TEMPLATE,
    TV_TEMPLATE,
    hardlink_or_copy,
    move_file,
    render_filename,
)
from backend.services.jellyfin_client import jellyfin_client
from backend.services.settings_service import get_setting
from backend.websocket_manager import manager

logger = get_logger("media_pipeline")

# Default minimum seeders for torrent results
DEFAULT_MIN_SEEDERS = 5

# Movie categories for Torznab/Newznab (2000 = Movies)
MOVIE_CATEGORIES = [2000, 2010, 2020, 2030, 2040, 2045, 2050, 2060]
# TV categories (5000 = TV)
TV_CATEGORIES = [5000, 5010, 5020, 5030, 5040, 5045, 5050, 5060]

# Common video file extensions
VIDEO_EXTENSIONS = {".mkv", ".mp4", ".avi", ".m4v", ".wmv", ".ts", ".flv", ".mov"}


async def schedule_request_processing(request_id: int) -> None:
    """Schedule request processing as a background task."""
    asyncio.create_task(_process_request_background(request_id))


async def _process_request_background(request_id: int) -> None:
    """Background task that creates its own DB session."""
    from backend.database import async_session

    async with async_session() as db:
        try:
            await process_approved_request(request_id, db)
            await db.commit()
        except Exception as e:
            logger.error("pipeline_failed", request_id=request_id, error=str(e))
            # Try to mark the request as failed
            try:
                result = await db.execute(
                    select(MediaRequest).where(MediaRequest.id == request_id)
                )
                request = result.scalar_one_or_none()
                if request and request.status not in (
                    RequestStatus.AVAILABLE,
                    RequestStatus.DENIED,
                ):
                    request.status = RequestStatus.FAILED
                    await db.commit()
                    await manager.broadcast(
                        "request:failed",
                        {"id": request_id, "error": str(e)},
                    )
            except Exception:
                logger.error("failed_to_mark_request_failed", request_id=request_id)


async def process_approved_request(request_id: int, db: AsyncSession) -> None:
    """Load an approved request and kick off the search pipeline."""
    result = await db.execute(
        select(MediaRequest).where(MediaRequest.id == request_id)
    )
    request = result.scalar_one_or_none()
    if not request:
        logger.error("request_not_found", request_id=request_id)
        return

    if request.status not in (RequestStatus.APPROVED, RequestStatus.SEARCHING):
        logger.warning(
            "request_not_approved",
            request_id=request_id,
            status=request.status.value,
        )
        return

    # Update status to searching
    request.status = RequestStatus.SEARCHING
    await db.flush()
    await manager.broadcast(
        "request:searching",
        {"id": request.id, "title": request.title},
    )

    if request.type == RequestType.MOVIE:
        await search_for_movie(request, db)
    elif request.type == RequestType.SERIES:
        await search_for_series(request, db)


async def search_for_movie(request: MediaRequest, db: AsyncSession) -> None:
    """Search indexers for a movie and start downloading the best result."""
    title = request.title
    tmdb_id = request.tmdb_id
    year = request.year

    # Get IMDB ID from TMDB external IDs
    imdb_id = None
    try:
        external_ids = await tmdb_client._get(f"/movie/{tmdb_id}/external_ids")
        imdb_id = external_ids.get("imdb_id")
    except Exception as e:
        logger.warning("tmdb_external_ids_failed", tmdb_id=tmdb_id, error=str(e))

    # Build search query with year for better matching
    query = f"{title} {year}" if year else title

    # Search all indexers
    results = await search_all_indexers(
        db,
        query=query,
        categories=MOVIE_CATEGORIES,
        imdb_id=imdb_id,
    )

    logger.info(
        "movie_search_complete",
        title=title,
        tmdb_id=tmdb_id,
        imdb_id=imdb_id,
        result_count=len(results),
    )

    # Filter by minimum seeders (for torrent results)
    min_seeders = await get_setting(db, "min_seeders", DEFAULT_MIN_SEEDERS)
    filtered = []
    for r in results:
        # Usenet results have no seeders field — always include them
        if r.seeders is None:
            filtered.append(r)
        elif r.seeders >= min_seeders:
            filtered.append(r)

    if not filtered:
        logger.warning("no_results_after_filter", title=title, raw_count=len(results))
        request.status = RequestStatus.FAILED
        await db.flush()
        await manager.broadcast(
            "request:failed",
            {"id": request.id, "title": title, "reason": "No suitable results found"},
        )
        return

    # Pick the best result: prefer quality, then seeders
    best = _pick_best_result(filtered)
    logger.info(
        "best_result_selected",
        title=best.title,
        indexer=best.indexer,
        seeders=best.seeders,
        size_bytes=best.size_bytes,
    )

    # Ensure we have a Movie record in the DB
    movie = await _ensure_movie_record(request, db)

    await start_download(best, request, db, movie_id=movie.id if movie else None)


async def search_for_series(request: MediaRequest, db: AsyncSession) -> None:
    """Search indexers for a TV series and start downloading."""
    title = request.title
    tmdb_id = request.tmdb_id
    tvdb_id = request.tvdb_id

    # Get tvdb_id from TMDB if we don't have it
    if not tvdb_id and tmdb_id:
        try:
            details = await tmdb_client.get_tv_details(tmdb_id)
            ext_ids = details.get("external_ids", {})
            tvdb_id = ext_ids.get("tvdb_id")
        except Exception as e:
            logger.warning("tmdb_tv_details_failed", tmdb_id=tmdb_id, error=str(e))

    # Determine which seasons are requested
    requested_seasons = None
    if request.requested_seasons:
        try:
            requested_seasons = json.loads(request.requested_seasons)
        except (json.JSONDecodeError, TypeError):
            pass

    # Ensure we have a Series record
    series = await _ensure_series_record(request, db)

    if requested_seasons:
        # Search for each specific season
        any_found = False
        for season_num in requested_seasons:
            found = await _search_season(
                title=title,
                season_num=season_num,
                tvdb_id=tvdb_id,
                request=request,
                series=series,
                db=db,
            )
            if found:
                any_found = True

        if not any_found:
            request.status = RequestStatus.FAILED
            await db.flush()
            await manager.broadcast(
                "request:failed",
                {
                    "id": request.id,
                    "title": title,
                    "reason": "No results found for requested seasons",
                },
            )
    else:
        # Try a complete series pack first
        query = f"{title} complete"
        results = await search_all_indexers(
            db,
            query=query,
            categories=TV_CATEGORIES,
            tvdb_id=tvdb_id,
        )

        min_seeders = await get_setting(db, "min_seeders", DEFAULT_MIN_SEEDERS)
        filtered = [
            r
            for r in results
            if r.seeders is None or r.seeders >= min_seeders
        ]

        if filtered:
            best = _pick_best_result(filtered)
            logger.info(
                "series_pack_found",
                title=best.title,
                indexer=best.indexer,
            )
            await start_download(best, request, db)
        else:
            # Fall back to searching individual seasons
            # Get season info from TMDB
            season_numbers = []
            try:
                details = await tmdb_client.get_tv_details(tmdb_id)
                for s in details.get("seasons", []):
                    sn = s.get("season_number", 0)
                    if sn > 0:  # Skip specials (season 0)
                        season_numbers.append(sn)
            except Exception as e:
                logger.warning("tmdb_season_list_failed", error=str(e))
                # Default to season 1 if we can't get the list
                season_numbers = [1]

            any_found = False
            for season_num in season_numbers:
                found = await _search_season(
                    title=title,
                    season_num=season_num,
                    tvdb_id=tvdb_id,
                    request=request,
                    series=series,
                    db=db,
                )
                if found:
                    any_found = True

            if not any_found:
                request.status = RequestStatus.FAILED
                await db.flush()
                await manager.broadcast(
                    "request:failed",
                    {
                        "id": request.id,
                        "title": title,
                        "reason": "No results found for any season",
                    },
                )


async def _search_season(
    title: str,
    season_num: int,
    tvdb_id: int | None,
    request: MediaRequest,
    series: Series | None,
    db: AsyncSession,
) -> bool:
    """Search for a single season. Returns True if a download was started."""
    # Format season query: "Show Name S01"
    query = f"{title} S{season_num:02d}"
    results = await search_all_indexers(
        db,
        query=query,
        categories=TV_CATEGORIES,
        tvdb_id=tvdb_id,
    )

    min_seeders = await get_setting(db, "min_seeders", DEFAULT_MIN_SEEDERS)
    filtered = [
        r for r in results if r.seeders is None or r.seeders >= min_seeders
    ]

    if not filtered:
        logger.warning("no_results_for_season", title=title, season=season_num)
        return False

    best = _pick_best_result(filtered)
    logger.info(
        "season_result_selected",
        title=best.title,
        season=season_num,
        indexer=best.indexer,
    )
    await start_download(best, request, db)
    return True


async def start_download(
    result: SearchResult,
    request: MediaRequest,
    db: AsyncSession,
    movie_id: int | None = None,
    episode_id: int | None = None,
) -> None:
    """Start downloading a search result."""
    # Determine download type
    download_url = result.download_url
    if result.info_hash or download_url.lower().endswith(".torrent"):
        dl_type = DownloadType.TORRENT
    elif download_url.lower().endswith(".nzb") or "newznab" in download_url.lower():
        dl_type = DownloadType.USENET
    else:
        # Default to torrent if we have seeders info, otherwise usenet
        dl_type = DownloadType.TORRENT if result.seeders is not None else DownloadType.USENET

    # Determine category
    if request.type == RequestType.MOVIE:
        category = DownloadCategory.MOVIES
    else:
        category = DownloadCategory.TV

    # Create the download record via the existing downloads service
    download_data = DownloadCreate(
        type=dl_type,
        title=result.title,
        download_url=download_url,
        category=category,
        movie_id=movie_id,
        episode_id=episode_id,
    )

    download = await add_download(download_data, db)

    # Store the indexer name on the download
    download.indexer_name = result.indexer
    download.size_bytes = result.size_bytes
    if result.info_hash and not download.info_hash:
        download.info_hash = result.info_hash

    # Update request status
    request.status = RequestStatus.DOWNLOADING
    await db.flush()

    logger.info(
        "download_started",
        download_id=download.id,
        title=result.title,
        type=dl_type.value,
        indexer=result.indexer,
        request_id=request.id,
    )

    await manager.broadcast(
        "request:downloading",
        {
            "id": request.id,
            "title": request.title,
            "download_id": download.id,
        },
    )


async def handle_download_complete(download_id: int, db: AsyncSession) -> None:
    """Handle post-download importing: move files, update library, notify."""
    result = await db.execute(
        select(Download).where(Download.id == download_id)
    )
    download = result.scalar_one_or_none()
    if not download:
        logger.error("download_not_found", download_id=download_id)
        return

    download.status = DownloadStatus.IMPORTING
    await db.flush()

    await manager.broadcast(
        "import:started",
        {"download_id": download.id, "title": download.title},
    )

    # Parse the release name for metadata
    parsed = parse_release_name(download.title)

    # Determine source and destination paths
    source_dir = _get_completed_download_path(download)
    source_file = _find_largest_video_file(source_dir)

    if not source_file:
        logger.error("no_video_file_found", download_id=download_id, source_dir=str(source_dir))
        download.status = DownloadStatus.FAILED
        download.error_message = "No video file found in completed download"
        await db.flush()
        await manager.broadcast(
            "import:failed",
            {"download_id": download.id, "title": download.title, "error": "No video file found"},
        )
        return

    ext = source_file.suffix

    if download.category == DownloadCategory.MOVIES:
        await _import_movie(download, parsed, source_file, ext, db)
    elif download.category == DownloadCategory.TV:
        await _import_tv(download, parsed, source_file, ext, db)
    else:
        # Generic import — just move to media root
        dest = settings.media_path / download.title
        dest.mkdir(parents=True, exist_ok=True)
        dest_file = dest / source_file.name
        _hardlink_or_move(source_file, dest_file)
        download.output_path = str(dest_file)

    download.status = DownloadStatus.IMPORTED
    await db.flush()

    # Trigger Jellyfin library refresh
    try:
        await jellyfin_client.refresh_library()
        logger.info("jellyfin_refresh_triggered", download_id=download_id)
    except Exception as e:
        logger.warning("jellyfin_refresh_failed", error=str(e))

    # Update any linked request to AVAILABLE
    await _update_request_status(download, RequestStatus.AVAILABLE, db)

    await manager.broadcast(
        "import:complete",
        {
            "download_id": download.id,
            "title": download.title,
            "output_path": download.output_path,
        },
    )

    # Log subtitle search trigger — the subtitle module handles the actual search
    logger.info(
        "subtitle_search_triggered",
        download_id=download_id,
        output_path=download.output_path,
    )


async def _import_movie(
    download: Download,
    parsed,
    source_file: Path,
    ext: str,
    db: AsyncSession,
) -> None:
    """Import a completed movie download into the library."""
    title = parsed.title or download.title
    year = parsed.year

    # Render the output filename using the naming template
    rendered = render_filename(
        MOVIE_TEMPLATE,
        title=title,
        year=year or "Unknown",
        quality=parsed.quality,
        codec=parsed.codec,
        ext=ext.lstrip("."),
    )
    dest_path = settings.media_path / "movies" / rendered
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    _hardlink_or_move(source_file, dest_path)

    download.output_path = str(dest_path)

    # Update the Movie record if linked
    if download.movie_id:
        movie_result = await db.execute(
            select(Movie).where(Movie.id == download.movie_id)
        )
        movie = movie_result.scalar_one_or_none()
        if movie:
            movie.file_path = str(dest_path)
            movie.quality = parsed.quality
            movie.codec = parsed.codec
            movie.resolution = parsed.quality  # quality typically holds resolution like 1080p
            movie.status = MediaStatus.AVAILABLE
            movie.file_size = source_file.stat().st_size if source_file.exists() else None
            logger.info("movie_record_updated", movie_id=movie.id, title=movie.title)


async def _import_tv(
    download: Download,
    parsed,
    source_file: Path,
    ext: str,
    db: AsyncSession,
) -> None:
    """Import a completed TV download into the library."""
    series_title = parsed.title or download.title
    season = parsed.season or 1
    episode = parsed.episode or 1

    rendered = render_filename(
        TV_TEMPLATE,
        series_title=series_title,
        season=season,
        episode=episode,
        episode_title=None,
        ext=ext.lstrip("."),
    )
    dest_path = settings.media_path / "tv" / rendered
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    _hardlink_or_move(source_file, dest_path)

    download.output_path = str(dest_path)

    # Update the Episode record if linked
    if download.episode_id:
        ep_result = await db.execute(
            select(Episode).where(Episode.id == download.episode_id)
        )
        ep = ep_result.scalar_one_or_none()
        if ep:
            ep.file_path = str(dest_path)
            ep.quality = parsed.quality
            ep.status = MediaStatus.AVAILABLE
            ep.file_size = source_file.stat().st_size if source_file.exists() else None
            logger.info(
                "episode_record_updated",
                episode_id=ep.id,
                season=season,
                episode=episode,
            )


def _pick_best_result(results: list[SearchResult]) -> SearchResult:
    """Pick the best result from filtered search results.

    Scoring: prioritize quality, then seeders/age.
    """
    quality_scores = {"2160p": 40, "1080p": 30, "720p": 20, "480p": 10}

    def score(r: SearchResult) -> int:
        s = 0
        # Quality bonus
        if r.quality:
            s += quality_scores.get(r.quality, 0)
        # Seeder bonus (torrent) — cap at 50 to not overwhelm quality
        if r.seeders is not None:
            s += min(r.seeders, 50)
        # Usenet results: prefer newer (lower age)
        if r.seeders is None and r.age_days is not None:
            s += max(0, 30 - r.age_days)  # newer = higher score
        # Use the pre-computed score from the indexer as a tiebreaker
        s += r.score
        return s

    results.sort(key=score, reverse=True)
    return results[0]


def _get_completed_download_path(download: Download) -> Path:
    """Determine where the completed download files are located."""
    if download.output_path:
        p = Path(download.output_path)
        if p.exists():
            return p

    # Convention: completed downloads go to download_path/complete/<title>
    complete_dir = settings.download_path / "complete"

    # Try exact title match
    candidate = complete_dir / download.title
    if candidate.exists():
        return candidate

    # Try without dots (some clients replace dots with spaces)
    clean_title = download.title.replace(".", " ")
    candidate2 = complete_dir / clean_title
    if candidate2.exists():
        return candidate2

    # Fall back to scanning the complete directory for a recent match
    if complete_dir.exists():
        # Get directories sorted by modification time (newest first)
        dirs = sorted(
            [d for d in complete_dir.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime,
            reverse=True,
        )
        # Check if the download title is a substring of any directory name
        title_lower = download.title.lower().replace(".", " ")
        for d in dirs:
            if title_lower[:20] in d.name.lower().replace(".", " "):
                return d

    # Final fallback: just use complete dir
    return complete_dir


def _find_largest_video_file(path: Path) -> Path | None:
    """Find the largest video file in a directory (or return the path if it's a file)."""
    if not path.exists():
        return None

    if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
        return path

    if not path.is_dir():
        return None

    largest = None
    largest_size = 0

    for f in path.rglob("*"):
        if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS:
            size = f.stat().st_size
            if size > largest_size:
                largest = f
                largest_size = size

    return largest


def _hardlink_or_move(src: Path, dst: Path) -> None:
    """Try hardlink first, fall back to move."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(src, dst)
        logger.info("hardlinked", src=str(src), dst=str(dst))
    except OSError:
        shutil.move(str(src), str(dst))
        logger.info("moved_fallback", src=str(src), dst=str(dst))


async def _ensure_movie_record(request: MediaRequest, db: AsyncSession) -> Movie | None:
    """Ensure a Movie record exists for this request, creating one if needed."""
    result = await db.execute(
        select(Movie).where(Movie.tmdb_id == request.tmdb_id)
    )
    movie = result.scalar_one_or_none()
    if movie:
        movie.status = MediaStatus.WANTED
        return movie

    # Create a new movie record from TMDB data
    try:
        from backend.modules.movies.schemas import MovieCreate
        from backend.modules.movies.service import add_movie

        data = MovieCreate(
            tmdb_id=request.tmdb_id,
            title=request.title,
            year=request.year,
            monitored=True,
        )
        movie = await add_movie(data, db)
        movie.status = MediaStatus.WANTED
        return movie
    except Exception as e:
        logger.warning("failed_to_create_movie_record", tmdb_id=request.tmdb_id, error=str(e))
        return None


async def _ensure_series_record(request: MediaRequest, db: AsyncSession) -> Series | None:
    """Ensure a Series record exists for this request, creating one if needed."""
    if request.tmdb_id:
        result = await db.execute(
            select(Series).where(Series.tmdb_id == request.tmdb_id)
        )
        series = result.scalar_one_or_none()
        if series:
            return series

    # Create a new series record
    try:
        from backend.modules.series.schemas import SeriesCreate
        from backend.modules.series.service import add_series

        data = SeriesCreate(
            tmdb_id=request.tmdb_id,
            tvdb_id=request.tvdb_id,
            title=request.title,
            year=request.year,
            monitored=True,
        )
        series = await add_series(data, db)
        return series
    except Exception as e:
        logger.warning("failed_to_create_series_record", tmdb_id=request.tmdb_id, error=str(e))
        return None


async def _update_request_status(
    download: Download,
    status: RequestStatus,
    db: AsyncSession,
) -> None:
    """Find and update the MediaRequest linked to this download."""
    # Find request by matching tmdb_id on linked movie or by title
    request = None

    if download.movie_id:
        movie_result = await db.execute(
            select(Movie).where(Movie.id == download.movie_id)
        )
        movie = movie_result.scalar_one_or_none()
        if movie:
            req_result = await db.execute(
                select(MediaRequest).where(
                    MediaRequest.tmdb_id == movie.tmdb_id,
                    MediaRequest.type == RequestType.MOVIE,
                    MediaRequest.status == RequestStatus.DOWNLOADING,
                )
            )
            request = req_result.scalar_one_or_none()

    if not request:
        # Try matching by title and downloading status
        req_result = await db.execute(
            select(MediaRequest).where(
                MediaRequest.status == RequestStatus.DOWNLOADING,
            ).order_by(MediaRequest.created_at.desc())
        )
        requests = list(req_result.scalars().all())
        title_lower = download.title.lower()
        for r in requests:
            if r.title and r.title.lower() in title_lower:
                request = r
                break

    if request:
        request.status = status
        await db.flush()
        logger.info(
            "request_status_updated",
            request_id=request.id,
            status=status.value,
        )
