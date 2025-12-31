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
from backend.agents.workflow import build_workflow, get_workflow

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
                        # Accumulate state instead of replacing
                        if final_state_ref["value"] is None:
                            final_state_ref["value"] = initial_state.copy()
                        final_state_ref["value"].update(node_output)  # Merge each node's output
                        
                        # Detect checkpoint immediately when researcher completes
                        if node_name == "researcher":
                            # Check if checkpoint reached (has research_context, no final_report)
                            if "research_context" in node_output and node_output.get("research_context") and not node_output.get("final_report_md"):
                                # Validate and ensure complete state structure before storing
                                accumulated_state = final_state_ref["value"]
                                
                                # Ensure profile is complete dict with required fields
                                if not isinstance(accumulated_state.get("profile"), dict):
                                    accumulated_state["profile"] = {}
                                profile = accumulated_state["profile"]
                                profile.setdefault("client_name", "Unknown")
                                profile.setdefault("assets", [])  # Always a list
                                profile.setdefault("tax_residency_current", "Unknown")
                                profile.setdefault("tax_residency_target", None)
                                profile.setdefault("marital_status", "Unknown")
                                profile.setdefault("specific_goals", [])
                                
                                # Ensure research_plan is complete dict with required fields
                                if not isinstance(accumulated_state.get("research_plan"), dict):
                                    accumulated_state["research_plan"] = {}
                                research_plan = accumulated_state["research_plan"]
                                research_plan.setdefault("queries", [])  # Always a list
                                research_plan.setdefault("rationale", "")
                                
                                # Now store complete validated state
                                workflow_states[thread_id] = accumulated_state
                                active_sessions[thread_id]["status"] = "checkpoint_reached"
                                await manager.send_checkpoint(thread_id)
                                # Stream will pause here due to interrupt_before=["writer"]
                                # Continue processing - stream naturally pauses
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
        
        # Store result - validate state structure
        final_state = final_state_ref["value"] or initial_state
        
        # Ensure state is a dict
        if not isinstance(final_state, dict):
            final_state = initial_state.copy()
        
        # Ensure required fields exist
        final_state.setdefault("profile", {})
        final_state.setdefault("research_plan", {})
        final_state.setdefault("research_context", "")
        final_state.setdefault("final_report_md", "")
        final_state.setdefault("approved_sources", [])
        final_state.setdefault("manual_notes", "")
        
        workflow_states[thread_id] = final_state
        
        # Check if workflow completed (checkpoint detection happens immediately in chunk processing)
        if "final_report_md" in final_state and final_state["final_report_md"]:
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


async def run_resume(thread_id: str, approved_sources: list, manual_notes: str):
    """Resume workflow from checkpoint via WebSocket"""
    try:
        # Store event loop reference for log streaming
        loop = asyncio.get_running_loop()
        manager.set_event_loop(loop)
        
        # Validate session exists
        if thread_id not in active_sessions:
            await manager.send_error(thread_id, "Session not found")
            return
        
        config = active_sessions[thread_id]["config"]
        workflow = get_workflow(websocket_manager=manager)
        
        # Update checkpoint state with new fields
        try:
            workflow.update_state(
                config,
                {
                    "approved_sources": approved_sources,
                    "manual_notes": manual_notes or ""
                }
            )
        except AttributeError:
            # Fallback to checkpointer access
            checkpointer = workflow.checkpointer
            checkpoint = checkpointer.get(config)
            if checkpoint:
                current_state = checkpoint.get("channel_values", {})
                current_state["approved_sources"] = approved_sources
                current_state["manual_notes"] = manual_notes or ""
                checkpointer.put(config, current_state)
        
        # Resume by streaming with None - use background thread pattern (same as steps 1-3)
        chunk_queue = queue.Queue()
        final_state_ref = {"value": None}
        stream_done = threading.Event()
        stream_error = {"value": None}
        
        def run_resume_stream():
            """Run workflow stream in sync thread"""
            try:
                for chunk in workflow.stream(None, config):
                    chunk_queue.put(chunk)
                stream_done.set()
            except Exception as e:
                import traceback
                stream_error["value"] = f"{str(e)}\n{traceback.format_exc()}"
                stream_done.set()
        
        # Start workflow stream in background thread
        stream_thread = threading.Thread(target=run_resume_stream, daemon=True)
        stream_thread.start()
        
        # Process chunks as they arrive (non-blocking, allows logs to stream in real-time)
        try:
            while not stream_done.is_set() or not chunk_queue.empty():
                try:
                    chunk = chunk_queue.get(timeout=0.1)
                    for node_name, node_output in chunk.items():
                        if node_name == "writer":
                            if final_state_ref["value"] is None:
                                final_state_ref["value"] = {}
                            final_state_ref["value"].update(node_output)
                            if "final_report_md" in final_state_ref["value"]:
                                break
                except queue.Empty:
                    pass
                await asyncio.sleep(0.05)
        finally:
            stream_thread.join(timeout=5)
            if stream_error["value"]:
                raise Exception(stream_error["value"])
        
        # Get final result
        result = final_state_ref["value"] if final_state_ref["value"] else {}
        
        # Update stored state
        workflow_states[thread_id] = result
        active_sessions[thread_id]["status"] = "completed"
        
        # Send completion messages
        await manager.send_progress(thread_id, "complete", 100)
        await manager.send_log(thread_id, "Report generation complete!", "success")
        await manager.send_complete(thread_id)
    
    except Exception as e:
        import traceback
        error_msg = f"Resume error: {str(e)}"
        print(f"ERROR in run_resume: {error_msg}")
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
                
                # Handle resume message
                elif message.get("type") == "resume":
                    approved_sources = message.get("approved_sources", [])
                    manual_notes = message.get("manual_notes", "")
                    
                    if not isinstance(approved_sources, list):
                        await manager.send_error(thread_id, "Invalid approved_sources in resume message")
                        continue
                    
                    # Resume workflow in background task
                    asyncio.create_task(run_resume(thread_id, approved_sources, manual_notes))
                
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

