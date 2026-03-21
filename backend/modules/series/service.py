from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.exceptions import NotFoundError
from backend.logging_config import get_logger
from backend.models.media import Episode, MediaStatus, Season, Series
from backend.modules.discovery.tmdb_client import tmdb_client
from backend.modules.series.schemas import SeriesCreate

logger = get_logger("series")


async def add_series(data: SeriesCreate, db: AsyncSession) -> Series:
    # Check existing
    if data.tmdb_id:
        result = await db.execute(select(Series).where(Series.tmdb_id == data.tmdb_id))
        existing = result.scalar_one_or_none()
        if existing:
            return existing

    # Fetch metadata
    details = {}
    if data.tmdb_id:
        details = await tmdb_client.get_tv_details(data.tmdb_id)

    poster = details.get("poster_path")
    backdrop = details.get("backdrop_path")
    first_air = details.get("first_air_date", "")

    series = Series(
        tmdb_id=data.tmdb_id,
        tvdb_id=data.tvdb_id or details.get("external_ids", {}).get("tvdb_id"),
        title=data.title or details.get("name", ""),
        overview=details.get("overview"),
        poster_url=f"https://image.tmdb.org/t/p/w500{poster}" if poster else None,
        backdrop_url=f"https://image.tmdb.org/t/p/w1280{backdrop}" if backdrop else None,
        rating=details.get("vote_average"),
        year=data.year or (int(first_air[:4]) if first_air else None),
        status_text=details.get("status"),
        network=details.get("networks", [{}])[0].get("name") if details.get("networks") else None,
        series_type=data.series_type,
        monitored=data.monitored,
        quality_profile_id=data.quality_profile_id,
        genres=str([g["name"] for g in details.get("genres", [])]),
    )
    db.add(series)
    await db.flush()

    # Create seasons
    for s in details.get("seasons", []):
        season = Season(
            series_id=series.id,
            season_number=s.get("season_number", 0),
            monitored=data.monitored,
            episode_count=s.get("episode_count", 0),
        )
        db.add(season)

    await db.flush()
    logger.info("series_added", title=series.title, tmdb_id=series.tmdb_id)
    return series


async def get_series(series_id: int, db: AsyncSession) -> Series:
    result = await db.execute(
        select(Series)
        .options(selectinload(Series.seasons))
        .where(Series.id == series_id)
    )
    series = result.scalar_one_or_none()
    if not series:
        raise NotFoundError("Series", series_id)
    return series


async def list_series(
    db: AsyncSession,
    monitored: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Series]:
    query = (
        select(Series)
        .options(selectinload(Series.seasons))
        .order_by(Series.title)
    )
    if monitored is not None:
        query = query.where(Series.monitored == monitored)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().unique().all())


async def get_episodes(series_id: int, season_number: int | None, db: AsyncSession) -> list[Episode]:
    query = select(Episode).where(Episode.series_id == series_id)
    if season_number is not None:
        query = query.join(Season).where(Season.season_number == season_number)
    query = query.order_by(Episode.episode_number)
    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_series(series_id: int, db: AsyncSession) -> None:
    series = await get_series(series_id, db)
    await db.delete(series)
    logger.info("series_deleted", title=series.title, id=series_id)
