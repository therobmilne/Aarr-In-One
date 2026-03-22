"""Downloads API — combines qBittorrent + SABnzbd via proxy."""

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.permissions import require_admin, require_power_user
from backend.logging_config import get_logger
from backend.models.user import User
from backend.services.arr_client import qbit_request, sabnzbd_request

logger = get_logger("downloads.router")

router = APIRouter(prefix="/downloads", tags=["downloads"])


def _map_qbit_status(state: str) -> str:
    """Map qBittorrent state to MediaForge status."""
    mapping = {
        "downloading": "downloading",
        "stalledDL": "downloading",
        "metaDL": "downloading",
        "forcedDL": "downloading",
        "uploading": "seeding",
        "stalledUP": "seeding",
        "forcedUP": "seeding",
        "pausedDL": "paused",
        "pausedUP": "paused",
        "queuedDL": "queued",
        "queuedUP": "queued",
        "checkingDL": "checking",
        "checkingUP": "checking",
        "checkingResumeData": "checking",
        "error": "error",
        "missingFiles": "error",
        "moving": "importing",
    }
    return mapping.get(state, "unknown")


@router.get("")
async def list_downloads(user: User = Depends(require_power_user)):
    """Combine active downloads from qBittorrent and SABnzbd."""
    downloads = []

    # Get torrents from qBittorrent
    try:
        resp = await qbit_request("GET", "/api/v2/torrents/info")
        if resp.status_code == 200:
            for t in resp.json():
                downloads.append({
                    "id": t["hash"],
                    "name": t["name"],
                    "type": "torrent",
                    "progress": round(t.get("progress", 0) * 100, 1),
                    "size": t.get("total_size", 0),
                    "download_speed": t.get("dlspeed", 0),
                    "upload_speed": t.get("upspeed", 0),
                    "seeds": t.get("num_seeds", 0),
                    "peers": t.get("num_leechs", 0),
                    "eta": t.get("eta", 0),
                    "status": _map_qbit_status(t.get("state", "unknown")),
                    "category": t.get("category", ""),
                    "added_on": t.get("added_on", 0),
                    "ratio": t.get("ratio", 0),
                })
    except Exception as e:
        logger.error("qbit_fetch_failed", error=str(e))

    # Get usenet downloads from SABnzbd
    try:
        data = await sabnzbd_request("queue")
        queue = data.get("queue", {})
        for slot in queue.get("slots", []):
            downloads.append({
                "id": slot.get("nzo_id", ""),
                "name": slot.get("filename", ""),
                "type": "usenet",
                "progress": float(slot.get("percentage", 0)),
                "size": int(float(slot.get("mb", 0)) * 1024 * 1024),
                "download_speed": float(queue.get("kbpersec", 0)) * 1024,
                "upload_speed": 0,
                "seeds": 0,
                "peers": 0,
                "eta": slot.get("timeleft", ""),
                "status": "downloading",
                "category": slot.get("cat", ""),
                "added_on": 0,
                "ratio": 0,
            })
    except Exception as e:
        logger.error("sabnzbd_fetch_failed", error=str(e))

    # Also get SABnzbd history for completed items
    try:
        hist = await sabnzbd_request("history", {"limit": 20})
        for slot in hist.get("history", {}).get("slots", []):
            downloads.append({
                "id": slot.get("nzo_id", ""),
                "name": slot.get("name", ""),
                "type": "usenet",
                "progress": 100.0,
                "size": int(float(slot.get("bytes", 0))),
                "download_speed": 0,
                "upload_speed": 0,
                "seeds": 0,
                "peers": 0,
                "eta": "",
                "status": "completed" if slot.get("status") == "Completed" else "failed",
                "category": slot.get("cat", ""),
                "added_on": 0,
                "ratio": 0,
            })
    except Exception:
        pass

    return downloads


@router.get("/stats")
async def download_stats(user: User = Depends(require_power_user)):
    """Get download statistics."""
    stats = {"active": 0, "paused": 0, "seeding": 0, "total_speed_down": 0, "total_speed_up": 0}

    try:
        resp = await qbit_request("GET", "/api/v2/transfer/info")
        if resp.status_code == 200:
            info = resp.json()
            stats["total_speed_down"] = info.get("dl_info_speed", 0)
            stats["total_speed_up"] = info.get("up_info_speed", 0)

        resp = await qbit_request("GET", "/api/v2/torrents/info")
        if resp.status_code == 200:
            for t in resp.json():
                s = _map_qbit_status(t.get("state", ""))
                if s in ("downloading", "checking"):
                    stats["active"] += 1
                elif s == "paused":
                    stats["paused"] += 1
                elif s == "seeding":
                    stats["seeding"] += 1
    except Exception:
        pass

    return stats


@router.post("/{download_id}/pause")
async def pause_download(download_id: str, user: User = Depends(require_power_user)):
    """Pause a torrent by hash or a usenet download by ID."""
    # Try qBittorrent first
    resp = await qbit_request("POST", "/api/v2/torrents/pause", data={"hashes": download_id})
    if resp.status_code == 200:
        return {"status": "paused", "id": download_id}

    # Try SABnzbd
    data = await sabnzbd_request("pause", {"value": download_id})
    if data.get("status"):
        return {"status": "paused", "id": download_id}

    raise HTTPException(status_code=404, detail="Download not found")


@router.post("/{download_id}/resume")
async def resume_download(download_id: str, user: User = Depends(require_power_user)):
    """Resume a paused download."""
    resp = await qbit_request("POST", "/api/v2/torrents/resume", data={"hashes": download_id})
    if resp.status_code == 200:
        return {"status": "resumed", "id": download_id}

    data = await sabnzbd_request("resume", {"value": download_id})
    if data.get("status"):
        return {"status": "resumed", "id": download_id}

    raise HTTPException(status_code=404, detail="Download not found")


@router.delete("/{download_id}")
async def delete_download(
    download_id: str,
    delete_files: bool = False,
    user: User = Depends(require_admin),
):
    """Remove a download."""
    resp = await qbit_request(
        "POST", "/api/v2/torrents/delete",
        data={"hashes": download_id, "deleteFiles": str(delete_files).lower()},
    )
    if resp.status_code == 200:
        return {"status": "deleted"}

    data = await sabnzbd_request("queue", {"name": "delete", "value": download_id})
    if data:
        return {"status": "deleted"}

    raise HTTPException(status_code=404, detail="Download not found")
