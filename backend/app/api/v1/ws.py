from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
from app.websocket.manager import ws_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/alerts")
async def websocket_alerts_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    await ws_manager.connect(websocket, token=token)
    try:
        while True:
            # Keep connection alive, listen for ping/pong or client inquiries
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket unexpected error: {e}")
        ws_manager.disconnect(websocket)
