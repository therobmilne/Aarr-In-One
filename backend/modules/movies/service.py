from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.exceptions import NotFoundError
from backend.logging_config import get_logger
from backend.models.media import MediaStatus, Movie
from backend.modules.discovery.tmdb_client import tmdb_client
from backend.modules.movies.schemas import MovieCreate

logger = get_logger("movies")


async def add_movie(data: MovieCreate, db: AsyncSession) -> Movie:
    # Check if already exists
    result = await db.execute(select(Movie).where(Movie.tmdb_id == data.tmdb_id))
    existing = result.scalar_one_or_none()
    if existing:
        return existing

    # Fetch TMDB metadata
    details = await tmdb_client.get_movie_details(data.tmdb_id)

    poster = details.get("poster_path")
    backdrop = details.get("backdrop_path")
    release_date = details.get("release_date", "")

    movie = Movie(
        tmdb_id=data.tmdb_id,
        imdb_id=details.get("imdb_id"),
        title=data.title or details.get("title", ""),
        original_title=details.get("original_title"),
        year=data.year or (int(release_date[:4]) if release_date else None),
        overview=details.get("overview"),
        poster_url=f"https://image.tmdb.org/t/p/w500{poster}" if poster else None,
        backdrop_url=f"https://image.tmdb.org/t/p/w1280{backdrop}" if backdrop else None,
        rating=details.get("vote_average"),
        runtime=details.get("runtime"),
        release_date=release_date,
        genres=str([g["name"] for g in details.get("genres", [])]),
        status=MediaStatus.WANTED if data.monitored else MediaStatus.MISSING,
        monitored=data.monitored,
        quality_profile_id=data.quality_profile_id,
    )
    db.add(movie)
    await db.flush()
    logger.info("movie_added", title=movie.title, tmdb_id=movie.tmdb_id)
    return movie


async def get_movie(movie_id: int, db: AsyncSession) -> Movie:
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    movie = result.scalar_one_or_none()
    if not movie:
        raise NotFoundError("Movie", movie_id)
    return movie


async def list_movies(
    db: AsyncSession,
    status: MediaStatus | None = None,
    monitored: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Movie]:
    query = select(Movie).order_by(Movie.title)
    if status:
        query = query.where(Movie.status == status)
    if monitored is not None:
        query = query.where(Movie.monitored == monitored)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def delete_movie(movie_id: int, db: AsyncSession, delete_files: bool = False) -> None:
    movie = await get_movie(movie_id, db)
    if delete_files and movie.file_path:
        import os
        try:
            os.remove(movie.file_path)
        except OSError:
            pass
    await db.delete(movie)
    logger.info("movie_deleted", title=movie.title, id=movie_id)
