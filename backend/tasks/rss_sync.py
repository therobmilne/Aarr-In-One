from backend.celery_app import celery
from backend.logging_config import get_logger

logger = get_logger("task.rss_sync")


@celery.task(name="backend.tasks.rss_sync.sync_rss_feeds")
def sync_rss_feeds():
    """Periodic RSS feed sync across all enabled indexers."""
    logger.info("rss_sync_started")
    # TODO: Query each indexer's RSS feed for new releases
    # Match against wanted movies/episodes
    # Auto-grab matching releases
    logger.info("rss_sync_completed")
