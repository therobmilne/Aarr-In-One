"""IPTV API — Xtream credentials + Threadfin integration.

This module handles IPTV credential management. Actual channel scanning
and M3U generation is handled by Threadfin (see livetv router).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.logging_config import get_logger
from backend.modules.iptv.schemas import IPTVCredentials, IPTVTestResult
from backend.modules.iptv.xtream_client import XtreamClient
from backend.services.settings_service import get_setting, set_setting

logger = get_logger("iptv.router")

router = APIRouter(prefix="/iptv", tags=["iptv"])


def _build_client(creds: IPTVCredentials) -> XtreamClient:
    return XtreamClient(
        server_url=creds.server_url,
        username=creds.username,
        password=creds.password,
    )


@router.post("/test", response_model=IPTVTestResult)
async def test_credentials(body: IPTVCredentials) -> IPTVTestResult:
    """Test IPTV credentials by authenticating."""
    client = _build_client(body)
    try:
        await client.test_connection()
    except ConnectionError as exc:
        return IPTVTestResult(success=False, message=str(exc))

    return IPTVTestResult(
        success=True,
        message="Connection successful",
    )


@router.get("/credentials")
async def get_credentials(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Return saved IPTV credentials with the password masked."""
    server_url = await get_setting(db, "iptv_server_url")
    username = await get_setting(db, "iptv_username")
    password = await get_setting(db, "iptv_password")

    if not all([server_url, username, password]):
        return {"configured": False}

    masked = password[:2] + "*" * max(len(password) - 2, 0) if password else ""
    return {
        "configured": True,
        "server_url": server_url,
        "username": username,
        "password": masked,
    }


@router.put("/credentials")
async def save_credentials(
    body: IPTVCredentials,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Save IPTV credentials to the database."""
    await set_setting(db, "iptv_server_url", body.server_url, category="iptv")
    await set_setting(db, "iptv_username", body.username, category="iptv")
    await set_setting(db, "iptv_password", body.password, category="iptv")
    return {"status": "saved"}
