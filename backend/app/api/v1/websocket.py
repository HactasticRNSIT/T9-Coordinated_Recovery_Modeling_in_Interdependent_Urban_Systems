from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import asyncio
import json
import redis.asyncio as aioredis
from app.core.config import settings

router = APIRouter()

# Connection manager for WebSocket clients
class ConnectionManager:
    def __init__(self):
        # incident_id -> set of WebSocket connections
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, incident_id: int):
        await websocket.accept()
        if incident_id not in self.active_connections:
            self.active_connections[incident_id] = set()
        self.active_connections[incident_id].add(websocket)

    def disconnect(self, websocket: WebSocket, incident_id: int):
        if incident_id in self.active_connections:
            self.active_connections[incident_id].discard(websocket)

    async def broadcast_to_incident(self, incident_id: int, message: dict):
        if incident_id not in self.active_connections:
            return
        dead_connections = set()
        for ws in self.active_connections[incident_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_connections.add(ws)
        # Clean up dead connections
        self.active_connections[incident_id] -= dead_connections


manager = ConnectionManager()


@router.websocket("/ws/incidents/{incident_id}")
async def incident_websocket(websocket: WebSocket, incident_id: int):
    """
    WebSocket endpoint for real-time node status updates.
    Subscribes to Redis pub/sub channel for the incident.
    """
    await manager.connect(websocket, incident_id)
    redis_client = aioredis.from_url(settings.REDIS_URL)
    pubsub = redis_client.pubsub()
    channel = f"incident:{incident_id}:updates"

    try:
        await pubsub.subscribe(channel)
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "incident_id": incident_id,
            "message": "Subscribed to real-time updates",
        })

        # Listen for messages from Redis pub/sub
        async def redis_listener():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await websocket.send_json(data)

        # Run listener and heartbeat concurrently
        async def heartbeat():
            while True:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                await websocket.send_json({"type": "heartbeat"})

        await asyncio.gather(redis_listener(), heartbeat())

    except WebSocketDisconnect:
        manager.disconnect(websocket, incident_id)
        await pubsub.unsubscribe(channel)
        await redis_client.close()
    except Exception as e:
        manager.disconnect(websocket, incident_id)
        await pubsub.unsubscribe(channel)
        await redis_client.close()


async def publish_node_update(incident_id: int, update_data: dict):
    """
    Publish a node status update to Redis pub/sub.
    Called by background tasks when node status changes.
    """
    redis_client = aioredis.from_url(settings.REDIS_URL)
    channel = f"incident:{incident_id}:updates"
    message = {
        "type": "node_status_update",
        **update_data
    }
    await redis_client.publish(channel, json.dumps(message))
    await redis_client.close()
