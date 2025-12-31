"""WebSocket endpoint for real-time progress updates"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
from typing import Dict, Optional
import json
import asyncio
import threading
import queue
import uuid

from backend.models import WSMessage
from backend.agents.workflow import build_workflow

# Store workflow states (shared with routes.py)
workflow_states: Dict[str, dict] = {}
active_sessions: Dict[str, dict] = {}

# Thread-safe queue for log messages from sync nodes
log_queue: queue.Queue = queue.Queue()


router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections for real-time updates"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.event_loop: Optional[asyncio.AbstractEventLoop] = None
    
    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Store event loop reference for thread-safe async calls"""
        self.event_loop = loop
    
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


async def run_workflow(thread_id: str, transcript: str):
    """Run workflow in background and stream updates via WebSocket"""
    try:
        # Store event loop reference BEFORE starting workflow thread
        # This allows sync nodes to access it via asyncio.run_coroutine_threadsafe
        loop = asyncio.get_running_loop()
        manager.set_event_loop(loop)
        
        await manager.send_log(thread_id, "Starting tax analysis workflow...", "info")
        await manager.send_progress(thread_id, "extracting", 10)
        
        # Store session
        config = {"configurable": {"thread_id": thread_id}}
        active_sessions[thread_id] = {
            "config": config,
            "started_at": datetime.now().isoformat(),
            "status": "processing"
        }
        
        # Build workflow with WebSocket manager
        workflow = build_workflow(websocket_manager=manager)
        
        # Initialize state
        initial_state = {
            "transcript": transcript,
            "thread_id": thread_id,
            "approved_sources": [],
            "manual_notes": "",
            "profile": {},
            "research_plan": {},
            "research_context": "",
            "final_report_md": ""
        }
        
        # Stream workflow execution
        await manager.send_log(thread_id, "Extracting client profile...", "info")
        
        # Use queue to pass chunks from sync thread to async handler
        chunk_queue = queue.Queue()
        final_state_ref = {"value": None}
        stream_done = threading.Event()
        stream_error = {"value": None}
        
        def run_workflow_stream():
            """Run workflow stream in sync thread"""
            try:
                chunk_count = 0
                for chunk in workflow.stream(initial_state, config):
                    chunk_count += 1
                    chunk_queue.put(chunk)
                stream_done.set()
            except Exception as e:
                import traceback
                stream_error["value"] = f"{str(e)}\n{traceback.format_exc()}"
                stream_done.set()
        
        # Start workflow stream in background thread
        stream_thread = threading.Thread(target=run_workflow_stream, daemon=True)
        stream_thread.start()
        
        # Process chunks as they arrive
        # Note: Logs are sent directly from nodes via asyncio.run_coroutine_threadsafe
        # No need to process log_queue here anymore
        try:
            while not stream_done.is_set() or not chunk_queue.empty():
                # Process workflow chunks
                try:
                    chunk = chunk_queue.get(timeout=0.1)
                    for node_name, node_output in chunk.items():
                        final_state_ref["value"] = node_output
                        # Progress updates are sent directly from nodes, no need to duplicate here
                except queue.Empty:
                    pass
                # Small sleep to prevent busy waiting
                await asyncio.sleep(0.05)
        
        finally:
            # No need to process remaining logs - they're sent directly from nodes
            pass
            
            stream_thread.join(timeout=5)
            if stream_error["value"]:
                raise Exception(stream_error["value"])
        
        # Store result
        final_state = final_state_ref["value"] or initial_state
        workflow_states[thread_id] = final_state
        
        # Check if checkpoint reached
        if "research_context" in final_state and final_state["research_context"] and not final_state.get("final_report_md"):
            await manager.send_progress(thread_id, "researching", 75)
            await manager.send_log(thread_id, "Research complete. Awaiting review...", "success")
            active_sessions[thread_id]["status"] = "checkpoint_reached"
            await manager.send_checkpoint(thread_id)
        elif "final_report_md" in final_state and final_state["final_report_md"]:
            await manager.send_progress(thread_id, "complete", 100)
            await manager.send_log(thread_id, "Report generation complete!", "success")
            active_sessions[thread_id]["status"] = "completed"
            await manager.send_complete(thread_id)
    
    except Exception as e:
        import traceback
        error_msg = f"Workflow error: {str(e)}"
        print(f"ERROR in run_workflow: {error_msg}")
        print(f"Traceback: {traceback.format_exc()}")
        await manager.send_error(thread_id, error_msg)
        if thread_id in active_sessions:
            active_sessions[thread_id]["status"] = "error"


@router.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    """
    WebSocket endpoint for real-time progress updates
    
    Clients connect with their thread_id to receive:
    - Log messages (terminal-style)
    - Progress updates
    - Checkpoint notifications
    - Completion/error notifications
    
    Clients can send:
    - {"type": "start", "transcript": "..."} - Start workflow
    """
    await manager.connect(thread_id, websocket)
    
    try:
        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle start message
                if message.get("type") == "start":
                    transcript = message.get("transcript")
                    if not transcript:
                        await manager.send_error(thread_id, "Missing transcript in start message")
                        continue
                    
                    # Start workflow in background task
                    asyncio.create_task(run_workflow(thread_id, transcript))
                
                # Handle ping/pong
                elif message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
            
            except json.JSONDecodeError:
                # Handle plain text messages (backward compatibility)
                if data == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
    
    except WebSocketDisconnect:
        manager.disconnect(thread_id)
        print(f"WebSocket disconnected: {thread_id}")
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(thread_id)

