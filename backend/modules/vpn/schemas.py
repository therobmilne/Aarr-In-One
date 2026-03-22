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


class VPNCredentials(BaseModel):
    provider: str
    connection_type: str  # "wireguard" or "openvpn"

    # WireGuard
    wireguard_config: str | None = None  # full wg0.conf contents

    # OpenVPN
    openvpn_username: str | None = None
    openvpn_password: str | None = None
    openvpn_config: str | None = None  # full .ovpn contents
    openvpn_server: str | None = None
    openvpn_port: int | None = None
    openvpn_protocol: str | None = None  # "udp" or "tcp"

    # General
    kill_switch: bool = True
    port_forwarding: bool = True
