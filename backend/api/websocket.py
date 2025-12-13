"""WebSocket endpoint for real-time progress updates"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
from typing import Dict
import json

from backend.models import WSMessage


router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, thread_id: str, websocket: WebSocket):
        """Accept and store WebSocket connection"""
        await websocket.accept()
        self.active_connections[thread_id] = websocket
        
        # Send connection confirmation
        await self.send_log(thread_id, "Connected to Hoxton Tax AI", "info")
    
    def disconnect(self, thread_id: str):
        """Remove WebSocket connection"""
        self.active_connections.pop(thread_id, None)
    
    async def send_log(
        self,
        thread_id: str,
        message: str,
        log_type: str = "info"
    ):
        """
        Send log message to client
        
        Args:
            thread_id: Client session ID
            message: Log message
            log_type: Type of log (info, success, error)
        """
        if thread_id not in self.active_connections:
            return
        
        try:
            msg = WSMessage(
                type="log",
                timestamp=datetime.now().isoformat(),
                data={"message": message, "log_type": log_type}
            )
            
            websocket = self.active_connections[thread_id]
            await websocket.send_text(msg.model_dump_json())
        
        except Exception as e:
            print(f"WebSocket send error: {e}")
            self.disconnect(thread_id)
    
    async def send_progress(
        self,
        thread_id: str,
        current_step: str,
        progress_percentage: int
    ):
        """Send progress update to client"""
        if thread_id not in self.active_connections:
            return
        
        try:
            msg = WSMessage(
                type="progress",
                timestamp=datetime.now().isoformat(),
                data={
                    "current_step": current_step,
                    "progress_percentage": progress_percentage
                }
            )
            
            websocket = self.active_connections[thread_id]
            await websocket.send_text(msg.model_dump_json())
        
        except Exception as e:
            print(f"WebSocket send error: {e}")
            self.disconnect(thread_id)
    
    async def send_checkpoint(self, thread_id: str):
        """Notify client that checkpoint has been reached"""
        if thread_id not in self.active_connections:
            return
        
        try:
            msg = WSMessage(
                type="checkpoint",
                timestamp=datetime.now().isoformat(),
                data={"message": "Checkpoint reached. Review required."}
            )
            
            websocket = self.active_connections[thread_id]
            await websocket.send_text(msg.model_dump_json())
        
        except Exception as e:
            print(f"WebSocket send error: {e}")
            self.disconnect(thread_id)
    
    async def send_complete(self, thread_id: str):
        """Notify client that workflow is complete"""
        if thread_id not in self.active_connections:
            return
        
        try:
            msg = WSMessage(
                type="complete",
                timestamp=datetime.now().isoformat(),
                data={"message": "Report generation complete!"}
            )
            
            websocket = self.active_connections[thread_id]
            await websocket.send_text(msg.model_dump_json())
        
        except Exception as e:
            print(f"WebSocket send error: {e}")
            self.disconnect(thread_id)
    
    async def send_error(self, thread_id: str, error_message: str):
        """Send error message to client"""
        if thread_id not in self.active_connections:
            return
        
        try:
            msg = WSMessage(
                type="error",
                timestamp=datetime.now().isoformat(),
                data={"message": error_message}
            )
            
            websocket = self.active_connections[thread_id]
            await websocket.send_text(msg.model_dump_json())
        
        except Exception as e:
            print(f"WebSocket send error: {e}")
            self.disconnect(thread_id)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    """
    WebSocket endpoint for real-time progress updates
    
    Clients connect with their thread_id to receive:
    - Log messages (terminal-style)
    - Progress updates
    - Checkpoint notifications
    - Completion/error notifications
    """
    await manager.connect(thread_id, websocket)
    
    try:
        # Keep connection alive and handle any client messages
        while True:
            data = await websocket.receive_text()
            
            # Handle client messages if needed (e.g., ping/pong)
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    
    except WebSocketDisconnect:
        manager.disconnect(thread_id)
        print(f"WebSocket disconnected: {thread_id}")
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(thread_id)

