from fastapi import APIRouter, Depends

from backend.auth.permissions import require_admin, require_power_user
from backend.models.user import User
from backend.modules.vpn.schemas import VPNStatusResponse
from backend.modules.vpn.service import vpn_engine

router = APIRouter(prefix="/vpn", tags=["vpn"])


@router.get("/status", response_model=VPNStatusResponse)
async def get_vpn_status(user: User = Depends(require_power_user)):
    return vpn_engine.get_status()


@router.post("/connect")
async def connect_vpn(user: User = Depends(require_admin)):
    success = await vpn_engine.connect()
    if success:
        return {"status": "connected", "ip": vpn_engine.get_status().public_ip}
    return {"status": "failed"}


@router.post("/disconnect")
async def disconnect_vpn(user: User = Depends(require_admin)):
    success = await vpn_engine.disconnect()
    return {"status": "disconnected" if success else "failed"}


@router.get("/port")
async def get_forwarded_port(user: User = Depends(require_power_user)):
    port = await vpn_engine.get_forwarded_port()
    return {"port": port}


@router.post("/health")
async def check_vpn_health(user: User = Depends(require_admin)):
    healthy = await vpn_engine.health_check()
    return {"healthy": healthy, "status": vpn_engine.get_status().model_dump()}
