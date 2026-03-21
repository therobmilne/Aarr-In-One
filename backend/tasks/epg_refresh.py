from backend.celery_app import celery
from backend.logging_config import get_logger

logger = get_logger("task.epg_refresh")


@celery.task(name="backend.tasks.epg_refresh.refresh_epg")
def refresh_epg():
    """Refresh EPG data from configured XMLTV sources."""
    import asyncio

    async def _refresh():
        from xml.etree import ElementTree

        import httpx
        from sqlalchemy import delete

        from backend.database import async_session
        from backend.models.livetv import EPGEntry
        from backend.services.settings_service import get_setting

        async with async_session() as db:
            epg_urls = await get_setting(db, "epg_urls", [])
            if not epg_urls:
                logger.info("no_epg_sources_configured")
                return

            # Clear existing EPG data
            await db.execute(delete(EPGEntry))

            total_entries = 0
            for url in epg_urls:
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        resp = await client.get(url)
                        resp.raise_for_status()

                    root = ElementTree.fromstring(resp.content)
                    for programme in root.findall(".//programme"):
                        entry = EPGEntry(
                            channel_epg_id=programme.get("channel", ""),
                            title=programme.findtext("title", ""),
                            description=programme.findtext("desc", ""),
                            start_time=programme.get("start", ""),
                            end_time=programme.get("stop", ""),
                            category=programme.findtext("category", ""),
                        )
                        db.add(entry)
                        total_entries += 1

                except Exception as e:
                    logger.error("epg_fetch_failed", url=url, error=str(e))

            await db.commit()
            logger.info("epg_refresh_completed", entries=total_entries)

    try:
        asyncio.get_event_loop().run_until_complete(_refresh())
    except RuntimeError:
        asyncio.run(_refresh())
