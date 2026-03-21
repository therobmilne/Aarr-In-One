"""Torrent download engine using libtorrent-rasterbar Python bindings."""

import asyncio
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.logging_config import get_logger

logger = get_logger("torrent")

# Try to import libtorrent, fall back gracefully
try:
    import libtorrent as lt

    HAS_LIBTORRENT = True
except ImportError:
    lt = None
    HAS_LIBTORRENT = False
    logger.warning("libtorrent_not_available", msg="Install libtorrent for torrent support")


class TorrentClient:
    def __init__(self):
        self._session: Any = None
        self._handles: dict[str, Any] = {}  # info_hash -> handle

    def _ensure_session(self):
        if not HAS_LIBTORRENT:
            raise RuntimeError("libtorrent is not installed")
        if self._session is None:
            sess_params = {
                "alert_mask": lt.alert.category_t.all_categories,
            }
            self._session = lt.session(sess_params)

            # Bind to VPN interface if available
            try:
                self._session.apply_settings({
                    "outgoing_interfaces": "tun0",
                    "listen_interfaces": "0.0.0.0:6881",
                })
            except Exception:
                logger.warning("vpn_bind_failed", msg="Could not bind to tun0")

            # Configure DHT and PeX
            self._session.apply_settings({
                "enable_dht": True,
                "enable_lsd": True,
            })

    async def add_torrent(
        self,
        url_or_magnet: str,
        save_path: str | None = None,
        category: str = "other",
    ) -> str:
        """Add a torrent by magnet link or URL. Returns info_hash."""
        self._ensure_session()
        download_path = save_path or str(settings.download_path / "torrents")
        Path(download_path).mkdir(parents=True, exist_ok=True)

        params = {"save_path": download_path}

        if url_or_magnet.startswith("magnet:"):
            params["url"] = url_or_magnet
        else:
            # Assume it's a .torrent URL, download it first
            import httpx
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url_or_magnet)
                resp.raise_for_status()
                ti = lt.torrent_info(lt.bdecode(resp.content))
                params["ti"] = ti

        handle = self._session.add_torrent(params)
        info_hash = str(handle.info_hash())
        self._handles[info_hash] = handle
        logger.info("torrent_added", info_hash=info_hash)
        return info_hash

    def get_status(self, info_hash: str) -> dict | None:
        handle = self._handles.get(info_hash)
        if not handle:
            return None
        s = handle.status()
        return {
            "info_hash": info_hash,
            "name": s.name,
            "progress": s.progress,
            "download_rate": s.download_rate,
            "upload_rate": s.upload_rate,
            "total_download": s.total_download,
            "total_upload": s.total_upload,
            "num_seeds": s.num_seeds,
            "num_peers": s.num_peers,
            "state": str(s.state),
            "is_seeding": s.is_seeding,
            "total_wanted": s.total_wanted,
            "total_wanted_done": s.total_wanted_done,
        }

    def pause(self, info_hash: str) -> bool:
        handle = self._handles.get(info_hash)
        if handle:
            handle.pause()
            return True
        return False

    def resume(self, info_hash: str) -> bool:
        handle = self._handles.get(info_hash)
        if handle:
            handle.resume()
            return True
        return False

    def remove(self, info_hash: str, delete_files: bool = False) -> bool:
        handle = self._handles.get(info_hash)
        if handle and self._session:
            flags = lt.options_t.delete_files if delete_files else 0
            self._session.remove_torrent(handle, flags)
            del self._handles[info_hash]
            return True
        return False

    def get_all_statuses(self) -> list[dict]:
        return [
            status for ih in list(self._handles.keys())
            if (status := self.get_status(ih)) is not None
        ]

    def update_port(self, port: int) -> None:
        """Update listening port (for VPN port forwarding)."""
        if self._session:
            self._session.apply_settings({
                "listen_interfaces": f"0.0.0.0:{port}",
            })
            logger.info("torrent_port_updated", port=port)

    def shutdown(self) -> None:
        if self._session:
            self._session.pause()
            self._session = None
            self._handles.clear()


torrent_client = TorrentClient()
