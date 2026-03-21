from backend.logging_config import get_logger
from backend.system.schemas import SubsystemHealth

logger = get_logger("health")


async def check_database() -> SubsystemHealth:
    try:
        from backend.database import engine

        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return SubsystemHealth(name="database", status="healthy")
    except Exception as e:
        return SubsystemHealth(name="database", status="error", message=str(e))


async def check_redis() -> SubsystemHealth:
    try:
        from backend.redis import redis_client

        if redis_client:
            await redis_client.ping()
            return SubsystemHealth(name="redis", status="healthy")
        return SubsystemHealth(name="redis", status="warning", message="Not connected")
    except Exception as e:
        return SubsystemHealth(name="redis", status="error", message=str(e))


async def check_jellyfin() -> SubsystemHealth:
    try:
        from backend.config import settings

        if not settings.JELLYFIN_URL:
            return SubsystemHealth(
                name="jellyfin", status="warning", message="Not configured"
            )
        from backend.services.jellyfin_client import jellyfin_client

        await jellyfin_client.test_connection()
        return SubsystemHealth(name="jellyfin", status="healthy")
    except Exception as e:
        return SubsystemHealth(name="jellyfin", status="error", message=str(e))


async def check_vpn() -> SubsystemHealth:
    import subprocess

    try:
        result = subprocess.run(
            ["ip", "link", "show", "tun0"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return SubsystemHealth(name="vpn", status="healthy")
        return SubsystemHealth(name="vpn", status="warning", message="tun0 not found")
    except FileNotFoundError:
        return SubsystemHealth(name="vpn", status="warning", message="ip command not available")
    except Exception as e:
        return SubsystemHealth(name="vpn", status="error", message=str(e))


async def get_all_health() -> list[SubsystemHealth]:
    return [
        await check_database(),
        await check_redis(),
        await check_jellyfin(),
        await check_vpn(),
    ]
