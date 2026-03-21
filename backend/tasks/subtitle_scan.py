from backend.celery_app import celery
from backend.logging_config import get_logger

logger = get_logger("task.subtitle_scan")


@celery.task(name="backend.tasks.subtitle_scan.scan_for_subtitles")
def scan_for_subtitles():
    """Scan media library for missing subtitles and download them."""
    import asyncio

    async def _scan():
        from backend.database import async_session
        from backend.models.media import MediaStatus, Movie
        from backend.modules.subtitles.service import download_best_subtitle
        from sqlalchemy import select

        async with async_session() as db:
            result = await db.execute(
                select(Movie).where(
                    Movie.status == MediaStatus.AVAILABLE,
                    Movie.file_path.isnot(None),
                )
            )
            movies = result.scalars().all()

            for movie in movies:
                if movie.file_path:
                    from pathlib import Path
                    srt_path = Path(movie.file_path).with_suffix(".srt")
                    if not srt_path.exists():
                        await download_best_subtitle(
                            movie.file_path,
                            languages=["en", "lt"],
                            min_score=60,
                        )

        logger.info("subtitle_scan_completed", movies_checked=len(movies))

    try:
        asyncio.get_event_loop().run_until_complete(_scan())
    except RuntimeError:
        asyncio.run(_scan())
