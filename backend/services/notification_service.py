import json
from typing import Any

import httpx

from backend.logging_config import get_logger

logger = get_logger("notifications")


async def send_discord_webhook(webhook_url: str, title: str, message: str, color: int = 0x6366F1):
    embed = {
        "embeds": [
            {
                "title": title,
                "description": message,
                "color": color,
                "footer": {"text": "MediaForge"},
            }
        ]
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(webhook_url, json=embed)
        except Exception as e:
            logger.error("discord_webhook_failed", error=str(e))


async def send_ntfy(url: str, topic: str, title: str, message: str):
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(
                f"{url}/{topic}",
                headers={"Title": title},
                content=message,
            )
        except Exception as e:
            logger.error("ntfy_failed", error=str(e))


async def send_gotify(url: str, token: str, title: str, message: str, priority: int = 5):
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(
                f"{url}/message",
                params={"token": token},
                json={"title": title, "message": message, "priority": priority},
            )
        except Exception as e:
            logger.error("gotify_failed", error=str(e))


async def dispatch_notification(
    agent_type: str, config: dict, event: str, title: str, message: str
):
    """Dispatch a notification based on agent type and config."""
    if agent_type == "discord":
        await send_discord_webhook(config.get("webhook_url", ""), title, message)
    elif agent_type == "ntfy":
        await send_ntfy(config.get("url", ""), config.get("topic", ""), title, message)
    elif agent_type == "gotify":
        await send_gotify(
            config.get("url", ""), config.get("token", ""), title, message
        )
    elif agent_type == "webhook":
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                await client.post(
                    config.get("url", ""),
                    json={"event": event, "title": title, "message": message},
                )
            except Exception as e:
                logger.error("webhook_failed", error=str(e))
    else:
        logger.warning("unknown_notification_type", type=agent_type)
