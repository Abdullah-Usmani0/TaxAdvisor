"""Tax consultancy agent nodes - extracted and refactored from agent2.py"""
import os
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
        # Determine LLM model based on API key availability
        llm_model = "gemini-3-pro-preview" if settings.google_api_key else "gemini-2.5-pro"
        
        self.llm = ChatGoogleGenerativeAI(model=llm_model, temperature=0)
        self.search_tool = TavilySearchResults(
            max_results=5,
            search_depth="advanced",
            include_raw_content=True
        )
        self.ws_manager = websocket_manager
    
    async def _send_log(self, thread_id: str, message: str, log_type: str = "info"):
        """Send log message via WebSocket if available"""
        if self.ws_manager and thread_id:
            await self.ws_manager.send_log(thread_id, message, log_type)
    
    # --- NODE 1: EXTRACTOR ---
    async def extract_profile(self, state: dict):
        """Extract client profile from transcript"""
        thread_id = state.get("thread_id", "")
        
        await self._send_log(thread_id, "Starting profile extraction...", "info")
        print(f"\n{'='*60}")
        print(f"🔍 [STEP 1/4] EXTRACTING CLIENT PROFILE")
        print(f"{'='*60}")
        
        transcript = state["transcript"]
        print(f"📝 Processing transcript ({len(transcript)} characters)...")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Tax Clerk. Extract the client profile strictly based on the transcript."),
            ("human", "{transcript}")
        ])
        
        extractor = prompt | self.llm.with_structured_output(ClientProfile)
        
        await self._send_log(thread_id, "Calling Gemini API for structured extraction...", "info")
        profile = extractor.invoke({"transcript": transcript})
        
        await self._send_log(thread_id, f"✓ Profile extracted: {profile.client_name}", "success")
        print(f"✅ Profile extracted successfully!")
        print(f"   - Client Name: {profile.client_name}")
        print(f"   - Current Tax Residency: {profile.tax_residency_current}")
        print(f"   - Target Tax Residency: {profile.tax_residency_target}")
        
        # Convert to dict for state
        return {"profile": profile.model_dump()}
    
    # --- NODE 2: PLANNER ---
    async def plan_research(self, state: dict):
        """Plan research strategy based on client profile"""
        thread_id = state.get("thread_id", "")
        profile_dict = state["profile"]
        profile = ClientProfile(**profile_dict)
        
        await self._send_log(thread_id, "Planning research strategy...", "info")
        print(f"\n{'='*60}")
        print(f"📋 [STEP 2/4] PLANNING RESEARCH STRATEGY")
        print(f"{'='*60}")
        print(f"🎯 Analyzing: {profile.tax_residency_current} → {profile.tax_residency_target}")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Senior Tax Partner. Plan the research for this client. Focus on Statutory Residence Tests, Double Tax Treaties, and specific local tax laws."),
            ("human", "Client Profile: {profile_data}")
        ])
        
        planner = prompt | self.llm.with_structured_output(ResearchPlan)
        plan = planner.invoke({"profile_data": profile.model_dump_json()})
        
        await self._send_log(thread_id, f"✓ Research plan created with {len(plan.queries)} queries", "success")
        print(f"✅ Research plan created!")
        print(f"   - Number of queries: {len(plan.queries)}")
        for i, query in enumerate(plan.queries, 1):
            print(f"   {i}. {query}")
        
        return {"research_plan": plan.model_dump()}
    
    # --- NODE 3: RESEARCHER ---
    async def execute_research(self, state: dict):
        """Execute research using Tavily search"""
        thread_id = state.get("thread_id", "")
        plan_dict = state["research_plan"]
        plan = ResearchPlan(**plan_dict)
        
        await self._send_log(thread_id, f"Starting research with {len(plan.queries)} queries...", "info")
        print(f"\n{'='*60}")
        print(f"🔎 [STEP 3/4] EXECUTING LEGAL RESEARCH")
        print(f"{'='*60}")
        
        compiled_research = []
        
        for i, query in enumerate(plan.queries, 1):
            try:
                await self._send_log(thread_id, f"→ Searching [{i}/{len(plan.queries)}]: {query[:50]}...", "info")
                print(f"   [{i}/{len(plan.queries)}] Searching: {query[:70]}...")
                
                enhanced_query = f"{query} current tax legislation 2024 2025"
                results = self.search_tool.invoke(enhanced_query)
                
                await self._send_log(thread_id, f"✓ Found {len(results)} sources", "success")
                print(f"       ✓ Found {len(results)} sources")
                
                snippet_text = "\n".join([
                    f"- Source: {r['url']}\n  Content: {r['content'][:500]}..." 
                    for r in results
                ])
                compiled_research.append(f"### Query: {query}\n{snippet_text}\n")
                
            except Exception as e:
                await self._send_log(thread_id, f"✗ Search failed: {str(e)}", "error")
                print(f"       ✗ Search failed: {e}")
        
        total_content = "\n".join(compiled_research)
        await self._send_log(thread_id, f"✓ Research complete! Gathered ~{len(plan.queries) * 5} sources", "success")
        print(f"\n✅ Research complete!")
        print(f"   - Research context size: {len(total_content)} characters")
        
        return {"research_context": total_content}
    
    # --- NODE 4: WRITER ---
    async def write_report(self, state: dict):
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
        
        await self._send_log(thread_id, "Writing comprehensive tax report...", "info")
        print(f"\n{'='*60}")
        print(f"✍️  [STEP 4/4] WRITING COMPREHENSIVE TAX REPORT")
        print(f"{'='*60}")
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
        
        await self._send_log(thread_id, "Generating report with Gemini...", "info")
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
        
        await self._send_log(thread_id, "✓ Report generated successfully!", "success")
        print(f"✅ Report generated successfully!")
        print(f"   - Report length: {len(report_text)} characters")
        
        return {"final_report_md": report_text}

