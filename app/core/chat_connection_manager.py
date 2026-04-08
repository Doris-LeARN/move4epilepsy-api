"""
Gestion des connexions WebSocket par canal de chat (diffusion en temps réel).
"""
import asyncio
from typing import Dict, List

from fastapi import WebSocket


class ChatConnectionManager:
    def __init__(self) -> None:
        self._rooms: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, channel_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms.setdefault(channel_id, []).append(websocket)

    async def disconnect(self, channel_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            room = self._rooms.get(channel_id)
            if not room:
                return
            self._rooms[channel_id] = [w for w in room if w is not websocket]
            if not self._rooms[channel_id]:
                del self._rooms[channel_id]

    async def broadcast_json(self, channel_id: str, data: dict) -> None:
        async with self._lock:
            targets = list(self._rooms.get(channel_id, []))
        dead: List[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(channel_id, ws)


chat_connection_manager = ChatConnectionManager()
