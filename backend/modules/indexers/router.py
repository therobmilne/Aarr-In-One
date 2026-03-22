"""Indexers API — proxies to Prowlarr."""

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.auth.permissions import require_admin, require_power_user
from backend.models.user import User
from backend.services.arr_client import prowlarr_request

router = APIRouter(prefix="/indexers", tags=["indexers"])


@router.get("")
async def list_indexers(user: User = Depends(require_power_user)):
    """Get all indexers from Prowlarr."""
    resp = await prowlarr_request("GET", "/api/v1/indexer")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch indexers from Prowlarr")
    return resp.json()


@router.post("")
async def add_indexer(data: dict, user: User = Depends(require_admin)):
    """Add an indexer to Prowlarr."""
    resp = await prowlarr_request("POST", "/api/v1/indexer", json=data)
    if resp.status_code in (200, 201):
        return resp.json()
    raise HTTPException(status_code=resp.status_code, detail=resp.text)


@router.get("/schema")
async def indexer_schema(user: User = Depends(require_admin)):
    """Get available indexer schemas from Prowlarr (for the Add Indexer UI)."""
    resp = await prowlarr_request("GET", "/api/v1/indexer/schema")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch indexer schemas")
    return resp.json()


@router.put("/{indexer_id}")
async def update_indexer(indexer_id: int, data: dict, user: User = Depends(require_admin)):
    """Update an indexer in Prowlarr."""
    resp = await prowlarr_request("PUT", f"/api/v1/indexer/{indexer_id}", json=data)
    if resp.status_code == 200:
        return resp.json()
    raise HTTPException(status_code=resp.status_code, detail=resp.text)


@router.delete("/{indexer_id}")
async def delete_indexer(indexer_id: int, user: User = Depends(require_admin)):
    """Delete an indexer from Prowlarr."""
    resp = await prowlarr_request("DELETE", f"/api/v1/indexer/{indexer_id}")
    if resp.status_code == 200:
        return {"status": "deleted"}
    raise HTTPException(status_code=resp.status_code, detail="Failed to delete indexer")


@router.post("/{indexer_id}/test")
async def test_indexer(indexer_id: int, user: User = Depends(require_admin)):
    """Test an indexer via Prowlarr."""
    # Get the indexer data first
    get_resp = await prowlarr_request("GET", f"/api/v1/indexer/{indexer_id}")
    if get_resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Indexer not found")

    indexer_data = get_resp.json()
    resp = await prowlarr_request("POST", "/api/v1/indexer/test", json=indexer_data)
    if resp.status_code == 200:
        return {"success": True, "message": "Indexer test passed"}
    return {"success": False, "message": resp.text}


@router.post("/test")
async def test_new_indexer(data: dict, user: User = Depends(require_admin)):
    """Test an indexer config before saving."""
    resp = await prowlarr_request("POST", "/api/v1/indexer/test", json=data)
    if resp.status_code == 200:
        return {"success": True}
    return {"success": False, "error": resp.text}


@router.get("/search")
async def search_indexers(
    q: str = Query("", description="Search query"),
    categories: str | None = Query(None, description="Comma-separated category IDs"),
    user: User = Depends(require_power_user),
):
    """Search across all indexers via Prowlarr."""
    params = {"query": q, "type": "search"}
    if categories:
        params["categories"] = categories
    resp = await prowlarr_request("GET", "/api/v1/search", params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Search failed")
    return resp.json()
