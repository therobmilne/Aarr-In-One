from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class VPNConfig(TimestampMixin, Base):
    __tablename__ = "vpn_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    vpn_type: Mapped[str] = mapped_column(String(20), nullable=False, default="wireguard")
    config_path: Mapped[str] = mapped_column(String(512), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    kill_switch: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    dns_leak_prevention: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # LAN bypass subnets (JSON array)
    lan_bypass_subnets: Mapped[str] = mapped_column(
        Text, nullable=False, default='["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]'
    )
    # Port forwarding
    port_forwarding_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    forwarded_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Status
    public_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
