"""LangGraph workflow with human-in-the-loop checkpointing"""
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from backend.agents.nodes import TaxConsultancyAgents


class TaxState(TypedDict):
    """State definition for tax consultancy workflow"""
    transcript: str
    profile: dict  # ClientProfile as dict
    research_plan: dict  # ResearchPlan as dict
    research_context: str
    approved_sources: list  # NEW: Indices of sources approved by human
    manual_notes: str  # NEW: Additional notes from human reviewer
    final_report_md: str
    thread_id: str


# Global shared checkpointer - ensures checkpoint state persists across workflow instances
_shared_checkpointer = MemorySaver()


def build_workflow(websocket_manager=None, checkpointer=None):
    """
    Build LangGraph workflow with checkpointing enabled
    
    Args:
        websocket_manager: Optional WebSocket manager for real-time updates
        checkpointer: Optional checkpointer instance (defaults to shared global)
    
    Returns:
        Compiled LangGraph app with checkpointing
    """
    # Initialize agents
    agents = TaxConsultancyAgents(websocket_manager=websocket_manager)
    
    # Create workflow graph
    workflow = StateGraph(TaxState)
    
    # Add nodes (convert sync methods to async-compatible)
    workflow.add_node("extractor", agents.extract_profile)
    workflow.add_node("planner", agents.plan_research)
    workflow.add_node("researcher", agents.execute_research)
    workflow.add_node("writer", agents.write_report)
    
    # Define edges (linear flow with interruption)
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "writer")  # Will interrupt before writer
    workflow.add_edge("writer", END)
    
    # Use shared checkpointer to ensure checkpoint state persists
    memory = checkpointer if checkpointer is not None else _shared_checkpointer
    app = workflow.compile(
        checkpointer=memory,
        interrupt_before=["writer"]  # Pause before writing report for human review
    )
    
    return app


# Global workflow instance (singleton pattern)
_workflow_app = None


def get_workflow(websocket_manager=None):
    """Get or create workflow instance"""
    global _workflow_app
    if _workflow_app is None:
        _workflow_app = build_workflow(websocket_manager)
    return _workflow_app

