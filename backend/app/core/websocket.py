import asyncio
import json
import logging
from typing import Dict, Set, List, Any, Optional, Callable
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from jose import jwt, JWTError

from app.core.config import settings
from app.core.security import oauth2_scheme, get_current_user
from app.db.models.user import User

logger = logging.getLogger(__name__)

class ConnectionManager:
    """WebSocket connection manager for real-time updates"""
    
    def __init__(self):
        # All active connections
        self.active_connections: List[WebSocket] = []
        # User ID to connections mapping
        self.user_connections: Dict[int, List[WebSocket]] = {}
        # Room to connections mapping (for workflow execution events)
        self.rooms: Dict[str, Set[WebSocket]] = {}
        # Connection to user mapping
        self.connection_user: Dict[WebSocket, User] = {}
        
    async def connect(self, websocket: WebSocket, user: User):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        # Store connection
        self.active_connections.append(websocket)
        
        # Store user connection
        if user.id not in self.user_connections:
            self.user_connections[user.id] = []
        self.user_connections[user.id].append(websocket)
        
        # Store user mapping
        self.connection_user[websocket] = user
        
        logger.info(f"WebSocket connection established for user {user.id}")
        
    def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        # Remove from active connections
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from user connections
        user = self.connection_user.get(websocket)
        if user and user.id in self.user_connections:
            if websocket in self.user_connections[user.id]:
                self.user_connections[user.id].remove(websocket)
            if not self.user_connections[user.id]:
                del self.user_connections[user.id]
        
        # Remove from rooms
        for room_name, connections in list(self.rooms.items()):
            if websocket in connections:
                connections.remove(websocket)
                if not connections:
                    del self.rooms[room_name]
        
        # Remove user mapping
        if websocket in self.connection_user:
            del self.connection_user[websocket]
            
        logger.info(f"WebSocket connection closed for user {user.id if user else 'unknown'}")
    
    async def join_room(self, websocket: WebSocket, room_name: str):
        """Add a connection to a specific room (e.g., workflow execution ID)"""
        if room_name not in self.rooms:
            self.rooms[room_name] = set()
        self.rooms[room_name].add(websocket)
        logger.debug(f"Connection joined room: {room_name}")
        
        # Send confirmation to client
        await self.send_personal_message(
            {"type": "room_joined", "room": room_name},
            websocket
        )
    
    async def leave_room(self, websocket: WebSocket, room_name: str):
        """Remove a connection from a specific room"""
        if room_name in self.rooms and websocket in self.rooms[room_name]:
            self.rooms[room_name].remove(websocket)
            if not self.rooms[room_name]:
                del self.rooms[room_name]
            logger.debug(f"Connection left room: {room_name}")
            
            # Send confirmation to client
            await self.send_personal_message(
                {"type": "room_left", "room": room_name},
                websocket
            )
    
    async def send_personal_message(self, message: Any, websocket: WebSocket):
        """Send a message to a specific client"""
        if isinstance(message, dict):
            await websocket.send_json(message)
        else:
            await websocket.send_text(str(message))
    
    async def broadcast(self, message: Any):
        """Broadcast a message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                if isinstance(message, dict):
                    await connection.send_json(message)
                else:
                    await connection.send_text(str(message))
            except RuntimeError:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_to_room(self, room_name: str, message: Any):
        """Broadcast a message to all clients in a specific room"""
        if room_name not in self.rooms:
            logger.warning(f"Attempted to broadcast to non-existent room: {room_name}")
            return
            
        disconnected = []
        for connection in self.rooms[room_name]:
            try:
                if isinstance(message, dict):
                    await connection.send_json(message)
                else:
                    await connection.send_text(str(message))
            except RuntimeError:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_to_user(self, user_id: int, message: Any):
        """Broadcast a message to all connections for a specific user"""
        if user_id not in self.user_connections:
            logger.warning(f"Attempted to broadcast to non-connected user: {user_id}")
            return
            
        disconnected = []
        for connection in self.user_connections[user_id]:
            try:
                if isinstance(message, dict):
                    await connection.send_json(message)
                else:
                    await connection.send_text(str(message))
            except RuntimeError:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# Singleton instance of the connection manager
manager = ConnectionManager()


async def get_token_from_websocket(websocket: WebSocket) -> Optional[str]:
    """Extract JWT token from WebSocket query params or cookies"""
    try:
        # Try to get token from query parameters
        token = websocket.query_params.get("token")
        if token:
            return token
            
        # Try to get token from cookies
        cookies = websocket.cookies
        token = cookies.get("access_token")
        if token:
            return token
            
        return None
    except Exception as e:
        logger.error(f"Error extracting token from WebSocket: {str(e)}")
        return None


async def get_user_from_websocket(websocket: WebSocket) -> Optional[User]:
    """Get the authenticated user from a WebSocket connection"""
    token = await get_token_from_websocket(websocket)
    if not token:
        return None
        
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
            
        from app.db.session import SessionLocal
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()
            return user
        finally:
            db.close()
    except JWTError:
        return None


# WebSocket connection event handlers
async def on_connect(websocket: WebSocket):
    """Handle new WebSocket connection"""
    user = await get_user_from_websocket(websocket)
    if not user:
        await websocket.close(code=1008)  # Policy violation
        return False
        
    await manager.connect(websocket, user)
    return True


async def on_disconnect(websocket: WebSocket):
    """Handle WebSocket disconnection"""
    manager.disconnect(websocket)


# Workflow execution specific events
async def send_workflow_started(execution_id: int, workflow_id: int, user_id: int):
    """Send workflow execution started event"""
    message = {
        "type": "workflow_started",
        "execution_id": execution_id,
        "workflow_id": workflow_id,
        "timestamp": str(asyncio.get_event_loop().time())
    }
    
    # Send to workflow room
    room_name = f"workflow_execution_{execution_id}"
    await manager.broadcast_to_room(room_name, message)
    
    # Send to user
    await manager.broadcast_to_user(user_id, message)


async def send_workflow_progress(execution_id: int, progress: int, current_node: Optional[str] = None):
    """Send workflow execution progress update"""
    message = {
        "type": "workflow_progress",
        "execution_id": execution_id,
        "progress": progress,
        "current_node": current_node,
        "timestamp": str(asyncio.get_event_loop().time())
    }
    
    room_name = f"workflow_execution_{execution_id}"
    await manager.broadcast_to_room(room_name, message)


async def send_workflow_completed(execution_id: int, success: bool, output: Optional[Dict[str, Any]] = None):
    """Send workflow execution completed event"""
    message = {
        "type": "workflow_completed",
        "execution_id": execution_id,
        "success": success,
        "output": output,
        "timestamp": str(asyncio.get_event_loop().time())
    }
    
    room_name = f"workflow_execution_{execution_id}"
    await manager.broadcast_to_room(room_name, message)


async def send_workflow_failed(execution_id: int, error: str):
    """Send workflow execution failed event"""
    message = {
        "type": "workflow_failed",
        "execution_id": execution_id,
        "error": error,
        "timestamp": str(asyncio.get_event_loop().time())
    }
    
    room_name = f"workflow_execution_{execution_id}"
    await manager.broadcast_to_room(room_name, message)


async def send_node_status(execution_id: int, node_id: int, status: str, output: Optional[Dict[str, Any]] = None):
    """Send node status update"""
    message = {
        "type": "node_status",
        "execution_id": execution_id,
        "node_id": node_id,
        "status": status,
        "output": output,
        "timestamp": str(asyncio.get_event_loop().time())
    }
    
    room_name = f"workflow_execution_{execution_id}"
    await manager.broadcast_to_room(room_name, message)


async def send_execution_log(execution_id: int, log_id: int, level: str, message: str, node_id: Optional[int] = None):
    """Send execution log event"""
    event = {
        "type": "execution_log",
        "execution_id": execution_id,
        "log_id": log_id,
        "level": level,
        "message": message,
        "node_id": node_id,
        "timestamp": str(asyncio.get_event_loop().time())
    }
    
    room_name = f"workflow_execution_{execution_id}"
    await manager.broadcast_to_room(room_name, event)