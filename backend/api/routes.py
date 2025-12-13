"""REST API endpoints for tax consultancy workflow"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from datetime import datetime
import uuid
import os
import markdown
from xhtml2pdf import pisa

from backend.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    StatusResponse,
    CheckpointData,
    CheckpointApprovalRequest,
    RefineResearchRequest
)
from backend.agents.workflow import get_workflow
from backend.agents.checkpoints import parse_research_sources, get_checkpoint_state_summary


router = APIRouter()

# In-memory storage for active sessions (MVP)
# TODO: Replace with Redis or PostgreSQL for production
active_sessions = {}
workflow_states = {}


@router.post("/analyze", response_model=AnalyzeResponse)
async def start_analysis(request: AnalyzeRequest):
    """
    Start tax analysis workflow
    
    - Validates transcript
    - Starts LangGraph workflow
    - Returns thread_id for tracking
    """
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        workflow = get_workflow()
        
        # Initialize state
        initial_state = {
            "transcript": request.transcript,
            "thread_id": thread_id,
            "approved_sources": [],
            "manual_notes": ""
        }
        
        # Start workflow (will pause at checkpoint)
        result = await workflow.ainvoke(initial_state, config)
        
        # Store session
        active_sessions[thread_id] = {
            "config": config,
            "started_at": datetime.now().isoformat(),
            "status": "checkpoint_reached"
        }
        workflow_states[thread_id] = result
        
        return AnalyzeResponse(
            thread_id=thread_id,
            status="checkpoint_reached",
            message="Research complete. Awaiting human review."
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/status/{thread_id}", response_model=StatusResponse)
async def get_status(thread_id: str):
    """Get current workflow status"""
    if thread_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state = workflow_states.get(thread_id, {})
    session = active_sessions[thread_id]
    
    # Determine current step based on state keys
    if "final_report_md" in state and state.get("final_report_md"):
        current_step = "complete"
        progress = 100
        is_paused = False
    elif "research_context" in state:
        current_step = "checkpoint"
        progress = 75
        is_paused = True
    elif "research_plan" in state:
        current_step = "researching"
        progress = 50
        is_paused = False
    elif "profile" in state:
        current_step = "planning"
        progress = 25
        is_paused = False
    else:
        current_step = "extracting"
        progress = 10
        is_paused = False
    
    return StatusResponse(
        thread_id=thread_id,
        current_step=current_step,
        progress_percentage=progress,
        is_paused=is_paused,
        error=None
    )


@router.get("/checkpoint/{thread_id}", response_model=CheckpointData)
async def get_checkpoint(thread_id: str):
    """
    Get research results for human review at checkpoint
    
    Returns:
        - Client profile
        - Research plan
        - All sources found
        - Timestamp
    """
    if thread_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state = workflow_states.get(thread_id, {})
    
    # Parse research sources
    research_context = state.get("research_context", "")
    sources = parse_research_sources(research_context)
    
    return CheckpointData(
        thread_id=thread_id,
        profile=state.get("profile", {}),
        research_plan=state.get("research_plan", {}),
        sources=sources,
        timestamp=datetime.now()
    )


@router.post("/checkpoint/approve")
async def approve_checkpoint(request: CheckpointApprovalRequest):
    """
    Resume workflow with human approval
    
    Actions:
    - approve: Continue with approved sources
    - refine: Re-run research with new queries
    - abort: Cancel workflow
    """
    thread_id = request.thread_id
    
    if thread_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if request.action == "abort":
        # Clean up session
        active_sessions.pop(thread_id, None)
        workflow_states.pop(thread_id, None)
        return {"status": "aborted", "message": "Workflow cancelled by user"}
    
    if request.action == "refine":
        # TODO: Implement research refinement
        raise HTTPException(status_code=501, detail="Research refinement not yet implemented")
    
    # Action: approve - continue workflow
    try:
        workflow = get_workflow()
        config = active_sessions[thread_id]["config"]
        
        # Update state with approved sources and notes
        current_state = workflow_states[thread_id]
        current_state["approved_sources"] = request.approved_sources
        current_state["manual_notes"] = request.manual_notes or ""
        
        # Resume workflow from checkpoint
        result = await workflow.ainvoke(current_state, config)
        
        # Update stored state
        workflow_states[thread_id] = result
        active_sessions[thread_id]["status"] = "completed"
        
        return {
            "status": "completed",
            "report_ready": True,
            "message": "Report generated successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Resume failed: {str(e)}")


@router.post("/checkpoint/refine")
async def refine_research(request: RefineResearchRequest):
    """Re-run research with refined queries"""
    # TODO: Implement research refinement
    raise HTTPException(status_code=501, detail="Not yet implemented")


@router.get("/download/{thread_id}")
async def download_pdf(thread_id: str):
    """Download generated PDF report"""
    if thread_id not in workflow_states:
        raise HTTPException(status_code=404, detail="Report not found")
    
    state = workflow_states[thread_id]
    report_md = state.get("final_report_md")
    
    if not report_md:
        raise HTTPException(status_code=400, detail="Report not yet generated")
    
    # Generate PDF
    pdf_filename = f"report_{thread_id}.pdf"
    pdf_path = f"/tmp/{pdf_filename}"
    
    try:
        generate_pdf_report(report_md, pdf_path)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=f"tax_report_{thread_id[:8]}.pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


def generate_pdf_report(markdown_content: str, filename: str):
    """Generate PDF from markdown report (from agent2.py)"""
    # Convert Markdown to HTML
    html_body = markdown.markdown(markdown_content, extensions=['tables'])
    
    # HTML Template with Hoxton branding
    html_template = f"""
    <html>
    <head>
        <style>
            @page {{
                size: A4;
                margin: 2.5cm;
            }}
            body {{
                font-family: "Helvetica", "Arial", sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #333333;
            }}
            h1 {{
                color: #1A4D2E;
                font-size: 24pt;
                border-bottom: 2px solid #1A4D2E;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            h2 {{
                color: #1A4D2E;
                font-size: 16pt;
                margin-top: 25px;
                border-bottom: 1px solid #cccccc;
                padding-bottom: 5px;
            }}
            h3 {{
                color: #34495e;
                font-size: 13pt;
                margin-top: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 10pt;
            }}
            th {{
                background-color: #1A4D2E;
                color: white;
                padding: 8px;
                border: 1px solid #dddddd;
            }}
            td {{
                border: 1px solid #dddddd;
                padding: 8px;
            }}
            .header {{
                text-align: right;
                color: #1A4D2E;
                font-size: 9pt;
                margin-bottom: 20px;
                border-bottom: 1px solid #1A4D2E;
                padding-bottom: 5px;
            }}
            .footer {{
                text-align: center;
                color: #555555;
                font-size: 9pt;
                margin-top: 40px;
                padding-top: 10px;
                border-top: 1px solid #cccccc;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <strong>Hoxton Tax Limited</strong> | Client Tax Report
        </div>
        {html_body}
        <div class="footer">
            Hoxton Tax Limited | Professional Tax Consultancy Services
        </div>
    </body>
    </html>
    """
    
    # Generate PDF
    with open(filename, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_template, dest=pdf_file)
    
    if pisa_status.err:
        raise Exception(f"PDF generation error: {pisa_status.err}")

