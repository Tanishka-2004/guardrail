import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from app.services.redis_service import redis_service
from app.core.security import decode_token

logger = logging.getLogger(__name__)

class WebSocketManager:
    """
    Manages live WebSocket client connections for analysts and supervisors.
    Supports:
    - Multi-instance event distribution via Redis Pub/Sub
    - Role-based event filtering
    - Keepalive heartbeats
    - Graceful connection termination and recovery
    """
    def __init__(self):
        # Maps user_id -> set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Maps WebSocket -> user info
        self.connection_users: Dict[WebSocket, Dict[str, Any]] = {}
        self._pubsub_task: Optional[asyncio.Task] = None
        self._is_running: bool = False

    async def start(self):
        self._is_running = True
        self._pubsub_task = asyncio.create_task(self._listen_redis_pubsub())
        logger.info("WebSocket manager started.")

    async def stop(self):
        self._is_running = False
        if self._pubsub_task:
            self._pubsub_task.cancel()
        for ws in list(self.connection_users.keys()):
            try:
                await ws.close(code=1001)
            except Exception:
                pass
        self.active_connections.clear()
        self.connection_users.clear()
        logger.info("WebSocket manager stopped.")

    async def connect(self, websocket: WebSocket, token: Optional[str] = None):
        await websocket.accept()
        user_info = {"id": "anonymous", "name": "Guest", "role": "ANALYST"}
        if token:
            try:
                payload = decode_token(token)
                user_info = {
                    "id": payload.get("sub", "unknown"),
                    "name": payload.get("name", "Analyst"),
                    "role": payload.get("role", "ANALYST"),
                }
            except Exception as e:
                logger.warning(f"Invalid WebSocket auth token: {e}")

        user_id = user_info["id"]
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        self.connection_users[websocket] = user_info

        # Send initial connected handshake
        await self.send_personal_message(
            websocket,
            {
                "event_type": "connection.established",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user": user_info,
                "active_connections_count": self.get_total_connections_count(),
            }
        )
        logger.info(f"WebSocket client connected: user={user_info['name']} ({user_info['role']})")

    def disconnect(self, websocket: WebSocket):
        user_info = self.connection_users.pop(websocket, None)
        if user_info:
            user_id = user_info["id"]
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        logger.info(f"WebSocket client disconnected: user={user_info.get('name') if user_info else 'unknown'}")

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        try:
            await websocket.send_text(json.dumps(message, default=str))
        except Exception as e:
            logger.warning(f"Error sending personal message over WebSocket: {e}")

    async def broadcast(self, event_type: str, payload: dict, target_role: Optional[str] = None):
        """
        Broadcasts an event locally and distributes via Redis Pub/Sub to other instances.
        """
        message = {
            "event_id": str(payload.get("id", "")),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_role": target_role,
            "payload": payload,
        }

        # 1. Publish to Redis channel for multi-instance broadcast
        await redis_service.publish_event(redis_service.CHANNEL_NAME, message)

        # 2. Local broadcast
        await self._local_broadcast(message)

    async def _local_broadcast(self, message: dict):
        target_role = message.get("target_role")
        dead_sockets = []

        for ws, user in list(self.connection_users.items()):
            if target_role and user.get("role") != target_role and user.get("role") != "ADMIN":
                continue
            try:
                await ws.send_text(json.dumps(message, default=str))
            except Exception:
                dead_sockets.append(ws)

        for ws in dead_sockets:
            self.disconnect(ws)

    async def _listen_redis_pubsub(self):
        """Subscribes to Redis Pub/Sub channel to receive events from all cluster nodes."""
        while self._is_running:
            if not redis_service.is_connected or not redis_service.client:
                await asyncio.sleep(3)
                continue
            try:
                pubsub = redis_service.client.pubsub()
                await pubsub.subscribe(redis_service.CHANNEL_NAME)
                logger.info(f"Subscribed to Redis Pub/Sub channel '{redis_service.CHANNEL_NAME}'")

                async for raw_message in pubsub.listen():
                    if not self._is_running:
                        break
                    if raw_message["type"] == "message":
                        try:
                            data = json.loads(raw_message["data"])
                            # Broadcast received multi-instance event to local connected websockets
                            await self._local_broadcast(data)
                        except Exception as e:
                            logger.error(f"Error processing Redis PubSub message: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Redis pubsub connection lost: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)

    def get_total_connections_count(self) -> int:
        return len(self.connection_users)

ws_manager = WebSocketManager()
