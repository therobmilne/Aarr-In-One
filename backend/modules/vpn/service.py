"""VPN engine: WireGuard/OpenVPN subprocess management, kill switch, port forwarding."""

import asyncio
import json
import subprocess
import time
from pathlib import Path

import httpx

from backend.config import settings
from backend.logging_config import get_logger
from backend.modules.vpn.schemas import VPNStatusResponse

logger = get_logger("vpn")


class VPNEngine:
    def __init__(self):
        self._process: asyncio.subprocess.Process | None = None
        self._connected = False
        self._public_ip: str | None = None
        self._forwarded_port: int | None = None
        self._start_time: float | None = None
        self._kill_switch_active = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self) -> bool:
        """Start VPN connection."""
        vpn_type = settings.VPN_TYPE
        config_path = settings.VPN_CONFIG_PATH

        if not Path(config_path).exists():
            logger.error("vpn_config_not_found", path=config_path)
            return False

        try:
            if vpn_type == "wireguard":
                await self._start_wireguard(config_path)
            elif vpn_type == "openvpn":
                await self._start_openvpn(config_path)
            else:
                logger.error("unknown_vpn_type", type=vpn_type)
                return False

            # Apply kill switch
            await self._apply_kill_switch()

            # Check connectivity
            await asyncio.sleep(3)
            self._public_ip = await self._get_public_ip()
            self._connected = True
            self._start_time = time.monotonic()

            logger.info("vpn_connected", ip=self._public_ip, type=vpn_type)
            return True

        except Exception as e:
            logger.error("vpn_connect_failed", error=str(e))
            return False

    async def disconnect(self) -> bool:
        """Stop VPN connection."""
        try:
            if settings.VPN_TYPE == "wireguard":
                proc = await asyncio.create_subprocess_exec(
                    "wg-quick", "down", settings.VPN_CONFIG_PATH,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
            elif self._process:
                self._process.terminate()
                await self._process.wait()
                self._process = None

            await self._remove_kill_switch()
            self._connected = False
            self._start_time = None
            self._public_ip = None
            logger.info("vpn_disconnected")
            return True
        except Exception as e:
            logger.error("vpn_disconnect_failed", error=str(e))
            return False

    async def _start_wireguard(self, config_path: str) -> None:
        proc = await asyncio.create_subprocess_exec(
            "wg-quick", "up", config_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"wg-quick failed: {stderr.decode()}")

    async def _start_openvpn(self, config_path: str) -> None:
        self._process = await asyncio.create_subprocess_exec(
            "openvpn", "--config", config_path,
            "--daemon", "--log", "/config/logs/openvpn.log",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

    async def _apply_kill_switch(self) -> None:
        """Apply iptables rules to prevent traffic leaking outside VPN tunnel."""
        rules = [
            # Allow loopback
            ["iptables", "-A", "OUTPUT", "-o", "lo", "-j", "ACCEPT"],
            # Allow VPN tunnel
            ["iptables", "-A", "OUTPUT", "-o", "tun0", "-j", "ACCEPT"],
            # Allow LAN traffic (bypass VPN for API communication)
            ["iptables", "-A", "OUTPUT", "-d", "192.168.0.0/16", "-j", "ACCEPT"],
            ["iptables", "-A", "OUTPUT", "-d", "10.0.0.0/8", "-j", "ACCEPT"],
            ["iptables", "-A", "OUTPUT", "-d", "172.16.0.0/12", "-j", "ACCEPT"],
            # Allow DNS
            ["iptables", "-A", "OUTPUT", "-p", "udp", "--dport", "53", "-j", "ACCEPT"],
            # Allow established connections
            ["iptables", "-A", "OUTPUT", "-m", "state", "--state", "ESTABLISHED,RELATED", "-j", "ACCEPT"],
            # Drop everything else
            ["iptables", "-A", "OUTPUT", "-j", "DROP"],
        ]

        for rule in rules:
            try:
                proc = await asyncio.create_subprocess_exec(
                    *rule,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
            except Exception as e:
                logger.warning("iptables_rule_failed", rule=" ".join(rule), error=str(e))

        self._kill_switch_active = True
        logger.info("kill_switch_applied")

    async def _remove_kill_switch(self) -> None:
        """Remove kill switch iptables rules."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "iptables", "-F", "OUTPUT",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            self._kill_switch_active = False
        except Exception as e:
            logger.warning("kill_switch_removal_failed", error=str(e))

    async def _get_public_ip(self) -> str | None:
        """Check public IP via external service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get("https://api.ipify.org?format=json")
                return resp.json().get("ip")
        except Exception:
            return None

    async def health_check(self) -> bool:
        """Verify VPN is still connected and working."""
        if not self._connected:
            return False

        # Check tun0 exists
        try:
            result = subprocess.run(
                ["ip", "link", "show", "tun0"],
                capture_output=True, timeout=5,
            )
            if result.returncode != 0:
                self._connected = False
                return False
        except Exception:
            pass

        # Check public IP hasn't changed
        ip = await self._get_public_ip()
        if ip and self._public_ip and ip != self._public_ip:
            logger.warning("vpn_ip_changed", old=self._public_ip, new=ip)
            self._public_ip = ip

        return True

    async def get_forwarded_port(self) -> int | None:
        """Get forwarded port from VPN provider (provider-specific)."""
        # ProtonVPN natpmpc method
        try:
            proc = await asyncio.create_subprocess_exec(
                "natpmpc", "-a", "0", "0", "udp", "60", "-g", "10.2.0.1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode()
            for line in output.split("\n"):
                if "Mapped public port" in line:
                    port = int(line.split()[-1])
                    self._forwarded_port = port
                    return port
        except Exception:
            pass

        return self._forwarded_port

    def get_status(self) -> VPNStatusResponse:
        uptime = None
        if self._start_time:
            uptime = time.monotonic() - self._start_time

        return VPNStatusResponse(
            connected=self._connected,
            provider=settings.VPN_PROVIDER,
            vpn_type=settings.VPN_TYPE,
            public_ip=self._public_ip,
            forwarded_port=self._forwarded_port,
            kill_switch_active=self._kill_switch_active,
            uptime_seconds=uptime,
        )


vpn_engine = VPNEngine()
