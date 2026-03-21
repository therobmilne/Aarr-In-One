from backend.celery_app import celery
from backend.logging_config import get_logger

logger = get_logger("task.library_sync")


@celery.task(name="backend.tasks.library_sync.sync_jellyfin_library")
def sync_jellyfin_library():
    """Sync Jellyfin library to update availability status."""
    import asyncio

    async def _sync():
        from backend.database import async_session
        from backend.models.media import MediaStatus, Movie, Series
        from backend.services.jellyfin_client import jellyfin_client
        from sqlalchemy import select

        try:
            libraries = await jellyfin_client.get_libraries()

            async with async_session() as db:
                for lib in libraries:
                    lib_type = lib.get("CollectionType", "")
                    if lib_type == "movies":
                        items = await jellyfin_client.get_items(
                            lib["Id"], include_type="Movie", limit=10000
                        )
                        jellyfin_titles = {
                            item.get("Name", "").lower(): item
                            for item in items.get("Items", [])
                        }

                        result = await db.execute(select(Movie))
                        for movie in result.scalars().all():
                            jf_item = jellyfin_titles.get(movie.title.lower())
                            if jf_item:
                                movie.status = MediaStatus.AVAILABLE
                                movie.jellyfin_id = jf_item.get("Id")
                            elif movie.status == MediaStatus.AVAILABLE:
                                movie.status = MediaStatus.MISSING

                    elif lib_type == "tvshows":
                        items = await jellyfin_client.get_items(
                            lib["Id"], include_type="Series", limit=10000
                        )
                        jellyfin_titles = {
                            item.get("Name", "").lower(): item
                            for item in items.get("Items", [])
                        }

                        result = await db.execute(select(Series))
                        for series in result.scalars().all():
                            jf_item = jellyfin_titles.get(series.title.lower())
                            if jf_item:
                                series.jellyfin_id = jf_item.get("Id")

                await db.commit()

            logger.info("library_sync_completed")
        except Exception as e:
            logger.error("library_sync_failed", error=str(e))

    try:
        asyncio.get_event_loop().run_until_complete(_sync())
    except RuntimeError:
        asyncio.run(_sync())
