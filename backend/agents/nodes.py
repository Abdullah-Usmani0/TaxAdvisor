"""Tax consultancy agent nodes - extracted and refactored from agent2.py"""
import os
import asyncio
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from backend.config import settings


# Pydantic Models for Agent Data
class ClientProfile(BaseModel):
    """Structured extraction of the client's status"""
    client_name: str = Field(description="Full name of the client")
    tax_residency_current: str = Field(description="Where they currently pay tax")
    tax_residency_target: Optional[str] = Field(description="Where they are moving/investing")
    assets: List[str] = Field(description="List of key assets (Properties, Pensions, Shares)")
    marital_status: str = Field(description="Relevant for transfer of assets/IHT")
    specific_goals: List[str] = Field(description="What they specifically want to achieve")


class ResearchPlan(BaseModel):
    """The strategy for what legal documents to find"""
    queries: List[str] = Field(description="List of specific search queries to run on Tavily")
    rationale: str = Field(description="Why we are searching for these specific things")


class TaxConsultancyAgents:
    """Agent nodes for tax consultancy workflow"""
    
    def __init__(self, websocket_manager=None):
        """
        Initialize agents with LLM and search tools
        
        Args:
            websocket_manager: Optional WebSocket manager for real-time updates
        """
        # Use gemini-2.5-pro (free tier compatible)
        llm_model = "gemini-2.5-pro"
        
        # Pass API key explicitly
        self.llm = ChatGoogleGenerativeAI(
            model=llm_model,
            temperature=0,
            google_api_key=settings.google_api_key
        )
        self.search_tool = TavilySearchResults(
            max_results=5,
            search_depth="advanced",
            include_raw_content=True,
            tavily_api_key=settings.tavily_api_key
        )
        self.ws_manager = websocket_manager
    
    def _send_log_sync(self, thread_id: str, message: str, log_type: str = "info"):
        """Send log message via WebSocket immediately (sync wrapper for async)"""
        if self.ws_manager and thread_id:
            try:
                # Get event loop from manager (stored when workflow starts)
                loop = getattr(self.ws_manager, 'event_loop', None)
                if not loop:
                    print(f"WARNING: No event loop for thread {thread_id} - log not sent: {message[:50]}")
                    return
                
                # Send log immediately using thread-safe coroutine runner
                # Fire and forget - don't wait for result
                asyncio.run_coroutine_threadsafe(
                    self.ws_manager.send_log(thread_id, message, log_type),
                    loop
                )
            except Exception as e:
                print(f"ERROR sending log: {e}")
                import traceback
                traceback.print_exc()
    
    def _send_progress_sync(self, thread_id: str, current_step: str, progress_percentage: int):
        """Send progress update via WebSocket immediately (sync wrapper for async)"""
        if self.ws_manager and thread_id:
            try:
                # Get event loop from manager (stored when workflow starts)
                loop = getattr(self.ws_manager, 'event_loop', None)
                if not loop:
                    print(f"WARNING: No event loop for thread {thread_id} - progress not sent")
                    return
                asyncio.run_coroutine_threadsafe(
                    self.ws_manager.send_progress(thread_id, current_step, progress_percentage),
                    loop
                )
            except Exception as e:
                print(f"ERROR sending progress: {e}")  # Temporary debug logging
    
    # --- NODE 1: EXTRACTOR ---
    def extract_profile(self, state: dict):
        """Extract client profile from transcript"""
        thread_id = state.get("thread_id", "")
        
        self._send_log_sync(thread_id, "🔍 [STEP 1/4] EXTRACTING CLIENT PROFILE", "info")
        print(f"\n{'='*60}")
        print(f"🔍 [STEP 1/4] EXTRACTING CLIENT PROFILE")
        print(f"{'='*60}")
        
        transcript = state["transcript"]
        self._send_log_sync(thread_id, f"📝 Processing transcript ({len(transcript)} characters)...", "info")
        print(f"📝 Processing transcript ({len(transcript)} characters)...")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Tax Clerk. Extract the client profile strictly based on the transcript."),
            ("human", "{transcript}")
        ])
        
        extractor = prompt | self.llm.with_structured_output(ClientProfile)
        profile = extractor.invoke({"transcript": transcript})
        
        self._send_log_sync(thread_id, "✅ Profile extracted successfully!", "success")
        self._send_log_sync(thread_id, f"   - Client Name: {profile.client_name}", "info")
        self._send_log_sync(thread_id, f"   - Current Tax Residency: {profile.tax_residency_current}", "info")
        self._send_log_sync(thread_id, f"   - Target Tax Residency: {profile.tax_residency_target}", "info")
        print(f"✅ Profile extracted successfully!")
        print(f"   - Client Name: {profile.client_name}")
        print(f"   - Current Tax Residency: {profile.tax_residency_current}")
        print(f"   - Target Tax Residency: {profile.tax_residency_target}")
        
        # Send progress update - extractor complete, move to planning
        self._send_progress_sync(thread_id, "planning", 25)
        
        # Convert to dict for state
        return {"profile": profile.model_dump()}
    
    # --- NODE 2: PLANNER ---
    def plan_research(self, state: dict):
        """Plan research strategy based on client profile"""
        thread_id = state.get("thread_id", "")
        profile_dict = state["profile"]
        profile = ClientProfile(**profile_dict)
        
        self._send_log_sync(thread_id, "📋 [STEP 2/4] PLANNING RESEARCH STRATEGY", "info")
        print(f"\n{'='*60}")
        print(f"📋 [STEP 2/4] PLANNING RESEARCH STRATEGY")
        print(f"{'='*60}")
        self._send_log_sync(thread_id, f"🎯 Analyzing: {profile.tax_residency_current} → {profile.tax_residency_target}", "info")
        print(f"🎯 Analyzing: {profile.tax_residency_current} → {profile.tax_residency_target}")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Senior Tax Partner. Plan the research for this client. Focus on Statutory Residence Tests, Double Tax Treaties, and specific local tax laws."),
            ("human", "Client Profile: {profile_data}")
        ])
        
        planner = prompt | self.llm.with_structured_output(ResearchPlan)
        plan = planner.invoke({"profile_data": profile.model_dump_json()})
        self._send_log_sync(thread_id, "✅ Research plan created!", "success")
        self._send_log_sync(thread_id, f"   - Number of queries: {len(plan.queries)}", "info")
        print(f"✅ Research plan created!")
        print(f"   - Number of queries: {len(plan.queries)}")
        for i, query in enumerate(plan.queries, 1):
            self._send_log_sync(thread_id, f"   {i}. {query}", "info")
            print(f"   {i}. {query}")
        
        # Send progress update - planner complete, move to researching
        self._send_progress_sync(thread_id, "researching", 50)
        
        return {"research_plan": plan.model_dump()}
    
    # --- NODE 3: RESEARCHER ---
    def execute_research(self, state: dict):
        """Execute research using Tavily search"""
        thread_id = state.get("thread_id", "")
        plan_dict = state["research_plan"]
        plan = ResearchPlan(**plan_dict)
        
        self._send_log_sync(thread_id, "🔎 [STEP 3/4] EXECUTING LEGAL RESEARCH", "info")
        print(f"\n{'='*60}")
        print(f"🔎 [STEP 3/4] EXECUTING LEGAL RESEARCH")
        print(f"{'='*60}")
        
        compiled_research = []
        
        for i, query in enumerate(plan.queries, 1):
            try:
                self._send_log_sync(thread_id, f"[{i}/{len(plan.queries)}] Searching: {query[:70]}...", "info")
                print(f"   [{i}/{len(plan.queries)}] Searching: {query[:70]}...")
                
                enhanced_query = f"{query} current tax legislation 2024 2025"
                results = self.search_tool.invoke(enhanced_query)
                
                self._send_log_sync(thread_id, f"✓ Found {len(results)} sources", "success")
                print(f"       ✓ Found {len(results)} sources")
                
                snippet_text = "\n".join([
                    f"- Source: {r['url']}\n  Content: {r['content'][:500]}..." 
                    for r in results
                ])
                compiled_research.append(f"### Query: {query}\n{snippet_text}\n")
                
            except Exception as e:
                self._send_log_sync(thread_id, f"✗ Search failed: {e}", "error")
                print(f"       ✗ Search failed: {e}")
        
        total_content = "\n".join(compiled_research)
        self._send_log_sync(thread_id, "✅ Research complete!", "success")
        self._send_log_sync(thread_id, f"   - Research context size: {len(total_content)} characters", "info")
        print(f"\n✅ Research complete!")
        print(f"   - Research context size: {len(total_content)} characters")
        
        # Send progress update - researcher complete, checkpoint reached (stays at researching until approved)
        self._send_progress_sync(thread_id, "researching", 75)
        
        return {"research_context": total_content}
    
    # --- NODE 4: WRITER ---
    def write_report(self, state: dict):
        """Generate comprehensive tax report"""
        thread_id = state.get("thread_id", "")
        profile_dict = state["profile"]
        profile = ClientProfile(**profile_dict)
        context = state["research_context"]
        
        # Apply checkpoint filtering if available
        approved_sources = state.get("approved_sources", [])
        manual_notes = state.get("manual_notes", "")
        
        # If approved sources specified, filter research context
        if approved_sources and context:
            # Simple filtering - in production, would parse and filter by index
            context = f"{context}\n\nHUMAN REVIEWER NOTES:\n{manual_notes}"
        
        self._send_log_sync(thread_id, "✍️  [STEP 4/4] WRITING COMPREHENSIVE TAX REPORT", "info")
        print(f"\n{'='*60}")
        print(f"✍️  [STEP 4/4] WRITING COMPREHENSIVE TAX REPORT")
        print(f"{'='*60}")
        self._send_log_sync(thread_id, f"📊 Preparing report for {profile.client_name}...", "info")
        print(f"📊 Preparing report for {profile.client_name}...")
        
        prompt_template = """
        You are a Tax Consultant at 'Hoxton Tax Limited'. Write a comprehensive, highly detailed Tax Report for {client_name}.
        
        STYLE GUIDE:
        - Use professional UK English.
        - The report must be detailed and analytical, providing clear legal basis for all conclusions.
        - **Crucial**: You must generate a "Day Count Scenario" table in the section on Statutory Residence Test (SRT) Analysis.
        - **Structure**: Use the following Markdown headings strictly:
          # Tax Residency & Planning Report for {client_name}
          ## Executive Summary
          ## Premise (Client Situation)
          ## UK Statutory Residence Test (SRT) Analysis
          ### Day Count Scenario Table
          ## Double Tax Treaty (DTT) Analysis: UK / {target_country}
          ### Tie-Breaker Clauses (Article 4)
          ## Recommendations and Planning Summary
          ## Disclaimer

        CLIENT DATA:
        {profile_json}

        LEGAL CONTEXT (Use this for citations and factual backing):
        {context}

        DISCLAIMER TEXT:
        "This report has been compiled based on UK tax legislation and guidance in force at the time of writing. Any tax laws, rates and allowances quoted are subject to change. If the tax law or practice changes, any planning undertaken may have to be revisited. We do not accept liability for losses arising from changes in the law or the interpretation thereof that are first published after the date of this report."
        """
        
        target_country = profile.tax_residency_target or "Target Country"
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm
        
        report = chain.invoke({
            "client_name": profile.client_name,
            "profile_json": profile.model_dump_json(),
            "target_country": target_country,
            "context": context
        })
        
        # Extract text content
        if isinstance(report.content, list):
            report_text = report.content[0].get('text', str(report.content))
        else:
            report_text = report.content
        
        self._send_log_sync(thread_id, "✅ Report generated successfully!", "success")
        self._send_log_sync(thread_id, f"   - Report length: {len(report_text)} characters", "info")
        print(f"✅ Report generated successfully!")
        print(f"   - Report length: {len(report_text)} characters")
        
        # Send progress update - writer complete, workflow finished
        self._send_progress_sync(thread_id, "writing", 100)
        
        return {"final_report_md": report_text}

