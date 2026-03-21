from pydantic import BaseModel


class VPNStatusResponse(BaseModel):
    connected: bool
    provider: str
    vpn_type: str
    public_ip: str | None
    forwarded_port: int | None
    kill_switch_active: bool
    uptime_seconds: float | None
    interface: str = "tun0"


class VPNConfigUpdate(BaseModel):
    provider: str | None = None
    vpn_type: str | None = None
    config_path: str | None = None
    kill_switch: bool | None = None
    dns_leak_prevention: bool | None = None
    port_forwarding_enabled: bool | None = None
    lan_bypass_subnets: list[str] | None = None
