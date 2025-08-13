"""
WebSocket router for real-time updates
"""
import json
import asyncio
from typing import Dict, Set, Any
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.websockets import WebSocketState
import logging

from shared.utils import setup_logging

logger = setup_logging("websocket", "INFO")

router = APIRouter()

class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "dashboard": set(),
            "jobs": set(),
            "queue": set(),
            "metrics": set(),
            "system": set()
        }
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, channel: str, client_id: str = None):
        """Accept a WebSocket connection and add to channel"""
        await websocket.accept()
        
        if channel not in self.active_connections:
            self.active_connections[channel] = set()
        
        self.active_connections[channel].add(websocket)
        self.connection_metadata[websocket] = {
            "channel": channel,
            "client_id": client_id,
            "connected_at": datetime.utcnow(),
            "last_ping": datetime.utcnow()
        }
        
        logger.info(f"WebSocket connected to channel '{channel}' with client_id '{client_id}'")
        
        # Send welcome message
        await self.send_personal_message({
            "type": "connection_established",
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat(),
            "message": f"Connected to {channel} channel"
        }, websocket)
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            channel = metadata["channel"]
            client_id = metadata.get("client_id")
            
            if channel in self.active_connections:
                self.active_connections[channel].discard(websocket)
            
            del self.connection_metadata[websocket]
            logger.info(f"WebSocket disconnected from channel '{channel}' with client_id '{client_id}'")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket connection"""
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending personal message: {e}")
                self.disconnect(websocket)
    
    async def broadcast_to_channel(self, message: dict, channel: str):
        """Broadcast message to all connections in a channel"""
        if channel not in self.active_connections:
            return
        
        message["timestamp"] = datetime.utcnow().isoformat()
        message_text = json.dumps(message)
        
        # Create a copy of connections to avoid modification during iteration
        connections = self.active_connections[channel].copy()
        
        for connection in connections:
            if connection.client_state == WebSocketState.CONNECTED:
                try:
                    await connection.send_text(message_text)
                except Exception as e:
                    logger.error(f"Error broadcasting to channel '{channel}': {e}")
                    self.disconnect(connection)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all active connections"""
        for channel in self.active_connections:
            await self.broadcast_to_channel(message, channel)
    
    def get_connection_stats(self) -> dict:
        """Get statistics about active connections"""
        stats = {
            "total_connections": sum(len(connections) for connections in self.active_connections.values()),
            "channels": {}
        }
        
        for channel, connections in self.active_connections.items():
            stats["channels"][channel] = {
                "active_connections": len(connections),
                "connections": []
            }
            
            for connection in connections:
                if connection in self.connection_metadata:
                    metadata = self.connection_metadata[connection]
                    stats["channels"][channel]["connections"].append({
                        "client_id": metadata.get("client_id"),
                        "connected_at": metadata["connected_at"].isoformat(),
                        "last_ping": metadata["last_ping"].isoformat()
                    })
        
        return stats

# Global connection manager instance
manager = ConnectionManager()

@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket, client_id: str = None):
    """WebSocket endpoint for dashboard real-time updates"""
    await manager.connect(websocket, "dashboard", client_id)
    try:
        while True:
            # Keep connection alive and handle ping/pong
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                # Update last ping time
                if websocket in manager.connection_metadata:
                    manager.connection_metadata[websocket]["last_ping"] = datetime.utcnow()
                
                # Send pong response
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
        manager.disconnect(websocket)

@router.websocket("/ws/jobs")
async def websocket_jobs(websocket: WebSocket, client_id: str = None):
    """WebSocket endpoint for job-related real-time updates"""
    await manager.connect(websocket, "jobs", client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                if websocket in manager.connection_metadata:
                    manager.connection_metadata[websocket]["last_ping"] = datetime.utcnow()
                
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Jobs WebSocket error: {e}")
        manager.disconnect(websocket)

@router.websocket("/ws/queue")
async def websocket_queue(websocket: WebSocket, client_id: str = None):
    """WebSocket endpoint for job queue status updates"""
    await manager.connect(websocket, "queue", client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                if websocket in manager.connection_metadata:
                    manager.connection_metadata[websocket]["last_ping"] = datetime.utcnow()
                
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Queue WebSocket error: {e}")
        manager.disconnect(websocket)

@router.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket, client_id: str = None):
    """WebSocket endpoint for system metrics streaming"""
    await manager.connect(websocket, "metrics", client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                if websocket in manager.connection_metadata:
                    manager.connection_metadata[websocket]["last_ping"] = datetime.utcnow()
                
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Metrics WebSocket error: {e}")
        manager.disconnect(websocket)

@router.websocket("/ws/system")
async def websocket_system(websocket: WebSocket, client_id: str = None):
    """WebSocket endpoint for system status updates"""
    await manager.connect(websocket, "system", client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                if websocket in manager.connection_metadata:
                    manager.connection_metadata[websocket]["last_ping"] = datetime.utcnow()
                
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"System WebSocket error: {e}")
        manager.disconnect(websocket)

# HTTP endpoint to get connection statistics
@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return manager.get_connection_stats()

# HTTP endpoint to broadcast messages (for testing and internal use)
@router.post("/ws/broadcast/{channel}")
async def broadcast_message(channel: str, message: dict):
    """Broadcast a message to all connections in a channel"""
    await manager.broadcast_to_channel(message, channel)
    return {"status": "message_sent", "channel": channel}

# Export the manager for use in other modules
__all__ = ["router", "manager"]