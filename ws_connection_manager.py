from fastapi import WebSocket
from typing import Dict, MutableMapping, Any


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_personal_message(self, message: str, client_id: str):
        websocket = self.active_connections.get(client_id)
        if websocket:
            await websocket.send_text(message)

    async def broadcast(self, message: str):
        for ws in self.active_connections.values():
            await ws.send_text(message)

    async def receive_text(self, client_id: str) -> str:
        websocket = self.active_connections.get(client_id)
        if not websocket:
            raise ValueError("Client not connected")

        return await websocket.receive_text()

# Singleton instance
ws_connection_manager = ConnectionManager()
