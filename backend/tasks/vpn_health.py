from backend.celery_app import celery
from backend.logging_config import get_logger

logger = get_logger("task.vpn_health")


@celery.task(name="backend.tasks.vpn_health.check_vpn_health")
def check_vpn_health():
    """Periodic VPN health check. Reconnects if needed."""
    import asyncio
    from backend.modules.vpn.service import vpn_engine

    async def _check():
        if vpn_engine.is_connected:
            healthy = await vpn_engine.health_check()
            if not healthy:
                logger.warning("vpn_unhealthy_reconnecting")
                await vpn_engine.disconnect()
                await vpn_engine.connect()

            # Update forwarded port
            port = await vpn_engine.get_forwarded_port()
            if port:
                from backend.modules.downloads.torrent_client import torrent_client
                torrent_client.update_port(port)

    try:
        asyncio.get_event_loop().run_until_complete(_check())
    except RuntimeError:
        asyncio.run(_check())
