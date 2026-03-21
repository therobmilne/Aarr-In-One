import asyncio
from collections import defaultdict
from typing import Any

import orjson
from fastapi import WebSocket

from backend.logging_config import get_logger

logger = get_logger("websocket")


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections[user_id].append(websocket)
        logger.info("ws_connected", user_id=user_id)

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        async with self._lock:
            conns = self.active_connections.get(user_id, [])
            if websocket in conns:
                conns.remove(websocket)
            if not conns:
                self.active_connections.pop(user_id, None)
        logger.info("ws_disconnected", user_id=user_id)

    async def broadcast(self, event: str, data: Any) -> None:
        message = orjson.dumps({"event": event, "data": data}).decode()
        async with self._lock:
            for user_id, connections in list(self.active_connections.items()):
                for ws in list(connections):
                    try:
                        await ws.send_text(message)
                    except Exception:
                        connections.remove(ws)

    async def send_to_user(self, user_id: str, event: str, data: Any) -> None:
        message = orjson.dumps({"event": event, "data": data}).decode()
        async with self._lock:
            for ws in list(self.active_connections.get(user_id, [])):
                try:
                    await ws.send_text(message)
                except Exception:
                    self.active_connections[user_id].remove(ws)

    @property
    def connection_count(self) -> int:
        return sum(len(v) for v in self.active_connections.values())


manager = ConnectionManager()
