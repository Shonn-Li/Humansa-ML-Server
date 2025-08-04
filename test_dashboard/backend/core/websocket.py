"""
WebSocket connection manager for real-time updates
"""

import json
import logging
from typing import Dict, List, Any
from collections import defaultdict

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Store connections by run_id
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)
        # Store connection metadata
        self.connection_data: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, run_id: str = None):
        """Accept and store a new WebSocket connection"""
        await websocket.accept()
        
        if run_id:
            self.active_connections[run_id].append(websocket)
        else:
            # General connections
            self.active_connections["general"].append(websocket)
        
        self.connection_data[websocket] = {
            "run_id": run_id,
            "connected_at": None
        }
        
        logger.info(f"WebSocket connected for run_id: {run_id}")
    
    def disconnect(self, websocket: WebSocket, run_id: str = None):
        """Remove a WebSocket connection"""
        if run_id and websocket in self.active_connections[run_id]:
            self.active_connections[run_id].remove(websocket)
            if not self.active_connections[run_id]:
                del self.active_connections[run_id]
        
        # Remove from general connections
        if websocket in self.active_connections["general"]:
            self.active_connections["general"].remove(websocket)
        
        # Remove metadata
        if websocket in self.connection_data:
            del self.connection_data[websocket]
        
        logger.info(f"WebSocket disconnected for run_id: {run_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
    
    async def broadcast_to_run(self, message: dict, run_id: str):
        """Broadcast a message to all connections for a specific run"""
        if run_id not in self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections[run_id]:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection, run_id)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast a message to all active connections"""
        disconnected = []
        
        for run_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Failed to broadcast message: {e}")
                    disconnected.append((connection, run_id))
        
        # Remove disconnected connections
        for connection, run_id in disconnected:
            self.disconnect(connection, run_id)
    
    async def send_run_update(self, run_id: str, update_type: str, data: dict):
        """Send a run-specific update"""
        message = {
            "type": "run_update",
            "run_id": run_id,
            "update_type": update_type,
            "data": data,
            "timestamp": None  # Add timestamp in production
        }
        await self.broadcast_to_run(message, run_id)
    
    async def send_system_update(self, update_type: str, data: dict):
        """Send a system-wide update"""
        message = {
            "type": "system_update",
            "update_type": update_type,
            "data": data,
            "timestamp": None  # Add timestamp in production
        }
        await self.broadcast_to_all(message)
    
    async def disconnect_all(self):
        """Disconnect all WebSocket connections"""
        for run_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.close()
                except:
                    pass
        
        self.active_connections.clear()
        self.connection_data.clear()
        logger.info("All WebSocket connections closed")
    
    def get_connection_count(self) -> Dict[str, int]:
        """Get count of active connections by run_id"""
        return {
            run_id: len(connections) 
            for run_id, connections in self.active_connections.items()
        }
    
    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())