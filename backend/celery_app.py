from celery import Celery
from celery.schedules import crontab

from backend.config import settings

celery = Celery(
    "mediaforge",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone=settings.TZ,
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "vpn-health-check": {
            "task": "backend.tasks.vpn_health.check_vpn_health",
            "schedule": 60.0,
        },
        "rss-sync": {
            "task": "backend.tasks.rss_sync.sync_rss_feeds",
            "schedule": 900.0,  # 15 minutes
        },
        "library-sync": {
            "task": "backend.tasks.library_sync.sync_jellyfin_library",
            "schedule": 3600.0,  # 1 hour
        },
        "subtitle-scan": {
            "task": "backend.tasks.subtitle_scan.scan_for_subtitles",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "epg-refresh": {
            "task": "backend.tasks.epg_refresh.refresh_epg",
            "schedule": crontab(minute=0, hour="*/12"),
        },
    },
)
