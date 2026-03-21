"""HDHomeRun device emulation for Jellyfin Live TV discovery."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from backend.config import settings
from backend.logging_config import get_logger

logger = get_logger("hdhr")

router = APIRouter(tags=["hdhr"])

DEVICE_ID = "MediaForge-HDHR"
DEVICE_MODEL = "MediaForge IPTV"


@router.get("/discover.json")
async def discover(request: Request):
    """HDHomeRun device discovery endpoint."""
    host = request.headers.get("host", f"localhost:{settings.APP_PORT}")
    base_url = f"http://{host}"

    return JSONResponse({
        "FriendlyName": DEVICE_MODEL,
        "Manufacturer": "MediaForge",
        "ModelNumber": "MFHDHR-1",
        "FirmwareName": "mediaforge",
        "FirmwareVersion": "0.1.0",
        "DeviceID": DEVICE_ID,
        "DeviceAuth": "mediaforge",
        "BaseURL": base_url,
        "LineupURL": f"{base_url}/lineup.json",
        "TunerCount": 4,
    })


@router.get("/lineup_status.json")
async def lineup_status():
    """HDHomeRun lineup scan status."""
    return JSONResponse({
        "ScanInProgress": 0,
        "ScanPossible": 1,
        "Source": "Cable",
        "SourceList": ["Cable"],
    })


@router.get("/lineup.json")
async def lineup(request: Request):
    """HDHomeRun channel lineup — lists all enabled IPTV channels."""
    from backend.database import async_session
    from backend.modules.livetv.service import list_channels

    host = request.headers.get("host", f"localhost:{settings.APP_PORT}")
    base_url = f"http://{host}"

    async with async_session() as db:
        channels = await list_channels(db, enabled=True)

    lineup_items = []
    for ch in channels:
        guide_number = str(ch.channel_number) if ch.channel_number else str(ch.id)
        lineup_items.append({
            "GuideNumber": guide_number,
            "GuideName": ch.name,
            "URL": f"{base_url}/api/v1/livetv/stream/{ch.id}",
        })

    return JSONResponse(lineup_items)
