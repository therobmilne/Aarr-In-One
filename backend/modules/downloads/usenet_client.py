"""Usenet download engine using nntplib for NNTP protocol."""

import asyncio
import hashlib
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.logging_config import get_logger

try:
    import nntplib  # Removed in Python 3.13, deprecated in 3.12
    HAS_NNTPLIB = True
except ImportError:
    HAS_NNTPLIB = False

logger = get_logger("usenet")


@dataclass
class UsenetServer:
    host: str
    port: int = 563
    username: str = ""
    password: str = ""
    use_ssl: bool = True
    connections: int = 8
    priority: int = 0  # 0 = primary, higher = backup


@dataclass
class NZBDownload:
    nzb_id: str
    title: str
    save_path: str
    total_bytes: int = 0
    downloaded_bytes: int = 0
    status: str = "queued"  # queued, downloading, par2_check, extracting, completed, failed
    error: str = ""
    speed_bytes_sec: int = 0


class UsenetClient:
    def __init__(self):
        self._servers: list[UsenetServer] = []
        self._downloads: dict[str, NZBDownload] = {}
        self._running = False

    def configure_servers(self, servers: list[dict]) -> None:
        self._servers = [
            UsenetServer(
                host=s["host"],
                port=s.get("port", 563),
                username=s.get("username", ""),
                password=s.get("password", ""),
                use_ssl=s.get("use_ssl", True),
                connections=s.get("connections", 8),
                priority=s.get("priority", 0),
            )
            for s in servers
        ]
        self._servers.sort(key=lambda s: s.priority)

    async def add_nzb(self, nzb_content: bytes, title: str, category: str = "other") -> str:
        """Add an NZB for download. Returns download ID."""
        nzb_id = hashlib.md5(nzb_content[:1024] + title.encode()).hexdigest()[:16]
        save_path = str(settings.download_path / "usenet" / category / title)
        Path(save_path).mkdir(parents=True, exist_ok=True)

        # Save NZB file
        nzb_path = os.path.join(save_path, f"{title}.nzb")
        with open(nzb_path, "wb") as f:
            f.write(nzb_content)

        self._downloads[nzb_id] = NZBDownload(
            nzb_id=nzb_id,
            title=title,
            save_path=save_path,
        )

        logger.info("nzb_added", nzb_id=nzb_id, title=title)
        return nzb_id

    async def add_nzb_url(self, url: str, title: str, category: str = "other") -> str:
        """Download NZB from URL and add it."""
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return await self.add_nzb(resp.content, title, category)

    def get_status(self, nzb_id: str) -> dict | None:
        dl = self._downloads.get(nzb_id)
        if not dl:
            return None
        progress = (dl.downloaded_bytes / dl.total_bytes * 100) if dl.total_bytes > 0 else 0
        return {
            "nzb_id": dl.nzb_id,
            "title": dl.title,
            "status": dl.status,
            "progress": progress,
            "downloaded_bytes": dl.downloaded_bytes,
            "total_bytes": dl.total_bytes,
            "speed_bytes_sec": dl.speed_bytes_sec,
            "error": dl.error,
        }

    def pause(self, nzb_id: str) -> bool:
        dl = self._downloads.get(nzb_id)
        if dl and dl.status == "downloading":
            dl.status = "paused"
            return True
        return False

    def resume(self, nzb_id: str) -> bool:
        dl = self._downloads.get(nzb_id)
        if dl and dl.status == "paused":
            dl.status = "queued"
            return True
        return False

    def remove(self, nzb_id: str) -> bool:
        if nzb_id in self._downloads:
            del self._downloads[nzb_id]
            return True
        return False

    def get_all_statuses(self) -> list[dict]:
        return [
            status for nid in list(self._downloads.keys())
            if (status := self.get_status(nid)) is not None
        ]

    @staticmethod
    async def run_par2_repair(directory: str) -> bool:
        """Run par2 repair on downloaded files."""
        par2_files = list(Path(directory).glob("*.par2"))
        if not par2_files:
            return True

        main_par2 = min(par2_files, key=lambda p: len(p.name))
        try:
            proc = await asyncio.create_subprocess_exec(
                "par2", "repair", str(main_par2),
                cwd=directory,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            return proc.returncode == 0
        except FileNotFoundError:
            logger.error("par2_not_found")
            return False

    @staticmethod
    async def extract_archives(directory: str) -> bool:
        """Extract RAR/ZIP archives in directory."""
        rar_files = list(Path(directory).glob("*.rar"))
        zip_files = list(Path(directory).glob("*.zip"))

        for rar in rar_files:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "unrar", "x", "-o+", str(rar), directory,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                if proc.returncode != 0:
                    return False
            except FileNotFoundError:
                logger.error("unrar_not_found")
                return False

        for zf in zip_files:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "7z", "x", "-o" + directory, "-y", str(zf),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
            except FileNotFoundError:
                logger.error("7z_not_found")

        return True

    def shutdown(self) -> None:
        self._running = False
        self._downloads.clear()


usenet_client = UsenetClient()
