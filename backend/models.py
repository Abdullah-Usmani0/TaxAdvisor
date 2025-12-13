"""Pydantic models for API requests, responses, and data validation"""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime


# Request Models
class AnalyzeRequest(BaseModel):
    """Request to start tax analysis workflow"""
    transcript: str = Field(min_length=50, description="Conversation transcript between advisor and client")


class CheckpointApprovalRequest(BaseModel):
    """Request to approve/refine/abort checkpoint"""
    thread_id: str
    approved_sources: List[int] = Field(description="Indices of approved research sources")
    manual_notes: Optional[str] = Field(default=None, description="Additional notes or documents from human reviewer")
    action: Literal["approve", "refine", "abort"]


class RefineResearchRequest(BaseModel):
    """Request to re-run research with new queries"""
    thread_id: str
    new_queries: List[str] = Field(description="Refined search queries")


# Response Models
class AnalyzeResponse(BaseModel):
    """Response after starting analysis"""
    thread_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    """Current workflow status"""
    thread_id: str
    current_step: Literal["extracting", "planning", "researching", "checkpoint", "writing", "complete", "error"]
    progress_percentage: int = Field(ge=0, le=100)
    is_paused: bool
    error: Optional[str] = None


class ResearchSource(BaseModel):
    """Individual research source from Tavily"""
    index: int
    url: str
    title: str
    snippet: str
    relevance_score: Optional[float] = None


class CheckpointData(BaseModel):
    """Data available at checkpoint for human review"""
    thread_id: str
    profile: dict  # ClientProfile data
    research_plan: dict
    sources: List[ResearchSource]
    timestamp: datetime


# WebSocket Message Models
class WSMessage(BaseModel):
    """WebSocket message format"""
    type: Literal["log", "progress", "checkpoint", "complete", "error"]
    timestamp: str
    data: dict

