from pydantic import BaseModel


class SubsystemHealth(BaseModel):
    name: str
    status: str  # healthy, warning, error
    message: str = ""


class HealthResponse(BaseModel):
    status: str  # healthy, degraded, unhealthy
    version: str = "0.1.0"
    subsystems: list[SubsystemHealth] = []


class DiskInfo(BaseModel):
    path: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    free_percent: float


class SystemInfo(BaseModel):
    version: str = "0.1.0"
    uptime_seconds: float = 0
    disk: list[DiskInfo] = []
    active_downloads: int = 0
    pending_requests: int = 0
    vpn_connected: bool = False
    websocket_connections: int = 0
