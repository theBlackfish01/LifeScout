"""
WebSocket Connection Manager for real-time communication.
Manages active connections per thread and broadcasts messages.
"""
import asyncio
import json
from typing import Dict, List
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections, keyed by thread_id."""

    def __init__(self):
        # thread_id -> list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, thread_id: str):
        await websocket.accept()
        async with self._lock:
            if thread_id not in self.active_connections:
                self.active_connections[thread_id] = []
            self.active_connections[thread_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, thread_id: str):
        async with self._lock:
            if thread_id in self.active_connections:
                self.active_connections[thread_id].remove(websocket)
                if not self.active_connections[thread_id]:
                    del self.active_connections[thread_id]

    async def send_json(self, thread_id: str, data: dict):
        """Send a JSON payload to all connections on a given thread."""
        async with self._lock:
            connections = self.active_connections.get(thread_id, [])
        for connection in connections:
            try:
                await connection.send_json(data)
            except Exception:
                pass  # Connection may be stale; cleanup handled on disconnect

    async def broadcast(self, data: dict):
        """Broadcast a JSON payload to ALL active connections across all threads."""
        async with self._lock:
            all_connections = [ws for conns in self.active_connections.values() for ws in conns]
        for connection in all_connections:
            try:
                await connection.send_json(data)
            except Exception:
                pass


# Singleton instance
manager = ConnectionManager()
