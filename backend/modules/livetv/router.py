"""Live TV API — proxies to Threadfin."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from backend.auth.permissions import require_admin, require_power_user
from backend.config import settings
from backend.logging_config import get_logger
from backend.models.user import User
from backend.services.arr_client import threadfin_request

logger = get_logger("livetv.router")

router = APIRouter(prefix="/livetv", tags=["livetv"])


class IPTVConfig(BaseModel):
    server_url: str
    username: str
    password: str
    name: str = "IPTV Provider"


@router.get("/status")
async def threadfin_status(user: User = Depends(require_power_user)):
    """Check Threadfin connection status."""
    try:
        resp = await threadfin_request("GET", "/api/")
        if resp.status_code == 200:
            return {"connected": True, "data": resp.json()}
    except Exception:
        pass
    return {"connected": False}


@router.get("/channels")
async def get_channels(user: User = Depends(require_power_user)):
    """Get channel list from Threadfin."""
    try:
        resp = await threadfin_request("GET", "/api/")
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error("threadfin_channels_failed", error=str(e))
    return []


@router.post("/iptv/config")
async def configure_iptv(data: IPTVConfig, user: User = Depends(require_admin)):
    """Add an M3U source to Threadfin from Xtream credentials."""
    m3u_url = (
        f"{data.server_url}/get.php?"
        f"username={data.username}&password={data.password}"
        f"&type=m3u_plus&output=ts"
    )
    xmltv_url = (
        f"{data.server_url}/xmltv.php?"
        f"username={data.username}&password={data.password}"
    )

    try:
        # Add M3U playlist to Threadfin
        await threadfin_request("POST", "/api/", json={
            "cmd": "saveNewM3U",
            "name": data.name,
            "url": m3u_url,
        })
        # Add XMLTV EPG to Threadfin
        await threadfin_request("POST", "/api/", json={
            "cmd": "saveNewXMLTV",
            "name": f"{data.name} EPG",
            "url": xmltv_url,
        })
    except Exception as e:
        logger.error("threadfin_iptv_config_failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"Failed to configure Threadfin: {e}")

    return {
        "status": "configured",
        "jellyfin_tuner_url": f"http://threadfin:34400",
        "jellyfin_epg_url": f"{settings.THREADFIN_URL}/xmltv/threadfin.xml",
    }


@router.post("/iptv/m3u")
async def add_m3u_playlist(
    name: str,
    url: str,
    user: User = Depends(require_admin),
):
    """Add a raw M3U URL to Threadfin."""
    try:
        await threadfin_request("POST", "/api/", json={
            "cmd": "saveNewM3U",
            "name": name,
            "url": url,
        })
        return {"status": "added", "name": name}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/output/m3u")
async def m3u_output():
    """Proxy Threadfin's M3U output."""
    try:
        resp = await threadfin_request("GET", "/m3u/threadfin.m3u")
        if resp.status_code == 200:
            return PlainTextResponse(resp.text, media_type="audio/x-mpegurl")
    except Exception:
        pass
    return PlainTextResponse("", media_type="audio/x-mpegurl")


@router.get("/epg.xml")
async def epg_xml():
    """Proxy Threadfin's XMLTV EPG output."""
    try:
        resp = await threadfin_request("GET", "/xmltv/threadfin.xml")
        if resp.status_code == 200:
            return PlainTextResponse(resp.text, media_type="application/xml")
    except Exception:
        pass
    return PlainTextResponse('<?xml version="1.0" encoding="utf-8"?><tv></tv>', media_type="application/xml")


@router.get("/stream/{channel_id}")
async def stream_channel(channel_id: str, request: Request):
    """Proxy a stream through Threadfin."""
    import httpx

    stream_url = f"{settings.THREADFIN_URL}/stream/{channel_id}"

    async def stream_generator():
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", stream_url) as resp:
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    yield chunk

    return StreamingResponse(
        stream_generator(),
        media_type="video/mp2t",
        headers={"Cache-Control": "no-cache"},
    )
