import os
import operator
from typing import List, Annotated, TypedDict, Optional, Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ----------------- LIBRARIES -----------------
# pip install langgraph langchain-google-genai langchain-community tavily-python markdown xhtml2pdf python-dotenv
# NOTE: Reverting to xhtml2pdf to fix the WeasyPrint system dependency issue.
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END
import markdown
from xhtml2pdf import pisa # Reverted to xhtml2pdf

# ----------------- CONFIGURATION -----------------
if not os.getenv("TAVILY_API_KEY"):
    print("Warning: TAVILY_API_KEY not found in environment variables.")
if not os.getenv("GOOGLE_API_KEY"):
    LLM_MODEL = "gemini-2.5-pro"
    print(f"Warning: GOOGLE_API_KEY not found. Using model: {LLM_MODEL}")
else:
    LLM_MODEL = "gemini-3-pro-preview"

# ----------------- 1. DATA MODELS -----------------

class ClientProfile(BaseModel):
    """Structured extraction of the client's status."""
    client_name: str = Field(description="Full name of the client")
    tax_residency_current: str = Field(description="Where they currently pay tax")
    tax_residency_target: Optional[str] = Field(description="Where they are moving/investing")
    assets: List[str] = Field(description="List of key assets (Properties, Pensions, Shares)")
    marital_status: str = Field(description="Relevant for transfer of assets/IHT")
    specific_goals: List[str] = Field(description="What they specifically want to achieve (e.g., 'Take 25% PCLS tax-free')")

class ResearchPlan(BaseModel):
    """The strategy for what legal documents to find."""
    queries: List[str] = Field(description="List of specific search queries to run on Tavily")
    rationale: str = Field(description="Why we are searching for these specific things")

# ----------------- 2. GRAPH STATE -----------------

class TaxState(TypedDict):
    """The shared memory of the entire consultation process."""
    transcript: str  # Input: The conversation text
    profile: ClientProfile  # Extracted data
    research_plan: ResearchPlan  # What we intend to search
    research_context: str  # Raw data found from Tavily
    final_report_md: str  # Output: The Markdown report

# ----------------- 3. NODES (The Agents) -----------------

class TaxConsultancyAgents:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=0)
        self.search_tool = TavilySearchResults(
            max_results=5, 
            search_depth="advanced", 
            include_raw_content=True
        )

    # --- NODE 1: EXTRACTOR ---
    def extract_profile(self, state: TaxState):
        print(f"\n{'='*60}")
        print(f"🔍 [STEP 1/4] EXTRACTING CLIENT PROFILE")
        print(f"{'='*60}")
        print(f"📝 Processing transcript ({len(state['transcript'])} characters)...")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Tax Clerk. Extract the client profile strictly based on the transcript."),
            ("human", "{transcript}")
        ])
        extractor = prompt | self.llm.with_structured_output(ClientProfile)
        
        print(f"🤖 Calling Gemini API for structured extraction...")
        profile = extractor.invoke({"transcript": state["transcript"]})
        
        print(f"✅ Profile extracted successfully!")
        print(f"   - Client Name: {profile.client_name}")
        print(f"   - Current Tax Residency: {profile.tax_residency_current}")
        print(f"   - Target Tax Residency: {profile.tax_residency_target}")
        print(f"   - Assets: {', '.join(profile.assets)}")
        print(f"   - Marital Status: {profile.marital_status}")
        print(f"   - Goals: {len(profile.specific_goals)} goal(s) identified")
        
        return {"profile": profile}

    # --- NODE 2: PLANNER ---
    def plan_research(self, state: TaxState):
        print(f"\n{'='*60}")
        print(f"📋 [STEP 2/4] PLANNING RESEARCH STRATEGY")
        print(f"{'='*60}")
        profile = state["profile"]
        profile_str = profile.model_dump_json()
        
        print(f"🎯 Analyzing client situation...")
        print(f"   - Focus: {profile.tax_residency_current} → {profile.tax_residency_target}")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Senior Tax Partner. Plan the research for this client. Focus on Statutory Residence Tests, Double Tax Treaties, and specific local tax laws (e.g., UK, KSA, Italy)."),
            ("human", "Client Profile: {profile_data}")
        ])
        
        planner = prompt | self.llm.with_structured_output(ResearchPlan)
        
        print(f"🤖 Generating research queries...")
        plan = planner.invoke({"profile_data": profile_str})
        
        print(f"✅ Research plan created!")
        print(f"   - Number of queries: {len(plan.queries)}")
        print(f"   - Rationale: {plan.rationale[:100]}...")
        for i, query in enumerate(plan.queries, 1):
            print(f"   {i}. {query}")
        
        return {"research_plan": plan}

    # --- NODE 3: RESEARCHER (TAVILY) ---
    def execute_research(self, state: TaxState):
        print(f"\n{'='*60}")
        print(f"🔎 [STEP 3/4] EXECUTING LEGAL RESEARCH")
        print(f"{'='*60}")
        plan = state["research_plan"]
        compiled_research = []

        print(f"🌐 Running {len(plan.queries)} deep web searches with Tavily...")
        print(f"   (This may take 1-2 minutes)\n")
        
        for i, query in enumerate(plan.queries, 1):
            try:
                print(f"   [{i}/{len(plan.queries)}] Searching: {query[:70]}...")
                enhanced_query = f"{query} current tax legislation 2024 2025"
                results = self.search_tool.invoke(enhanced_query)
                
                print(f"       ✓ Found {len(results)} sources")
                snippet_text = "\n".join([f"- Source: {r['url']}\n  Content: {r['content'][:500]}..." for r in results])
                compiled_research.append(f"### Query: {query}\n{snippet_text}\n")
            except Exception as e:
                print(f"       ✗ Search failed: {e}")

        total_content = "\n".join(compiled_research)
        print(f"\n✅ Research complete!")
        print(f"   - Total sources gathered: ~{len(plan.queries) * 5}")
        print(f"   - Research context size: {len(total_content)} characters")
        
        return {"research_context": total_content}

    # --- NODE 4: WRITER (HIGH DETAIL) ---
    def write_report(self, state: TaxState):
        print(f"\n{'='*60}")
        print(f"✍️  [STEP 4/4] WRITING COMPREHENSIVE TAX REPORT")
        print(f"{'='*60}")
        profile = state["profile"]
        context = state["research_context"]

        print(f"📊 Preparing report for {profile.client_name}...")
        print(f"   - Using {len(context)} chars of legal research")
        print(f"   - Target country: {profile.tax_residency_target}")
        print(f"🤖 Generating detailed report with Gemini (this may take 30-60 seconds)...")
        
        # CRITICAL: This prompt is enhanced to enforce the detailed, Hoxton-style structure.
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
        "This report has been compiled based on UK tax legislation and guidance in force at the time of writing. Any tax laws, rates and allowances quoted are subject to change. If the tax law or practice changes, any planning undertaken may have to be revisited. We do not accept liability for losses arising from changes in the law or the interpretation thereof that are first published after the date of this report. If you are in any doubt, you should seek confirmation from us that the advice is still valid in the light of any change in the law or your circumstances. The report is not to be relied on by third parties and Hoxton Tax Limited cannot be held responsible for any action taken, or refrained from having been taken, by any third party based on this report."
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
        
        # Extract text content from the response
        if isinstance(report.content, list):
            # Handle list response format from Gemini
            report_text = report.content[0]['text'] if report.content and 'text' in report.content[0] else str(report.content)
        else:
            report_text = report.content
        
        print(f"✅ Report generated successfully!")
        print(f"   - Report length: {len(report_text)} characters")
        print(f"   - Sections included: Executive Summary, SRT Analysis, DTT Analysis, Recommendations")
        
        return {"final_report_md": report_text}

# ----------------- 4. GRAPH CONSTRUCTION -----------------

def build_tax_app():
    agents = TaxConsultancyAgents()
    workflow = StateGraph(TaxState)

    # Add Nodes
    workflow.add_node("extractor", agents.extract_profile)
    workflow.add_node("planner", agents.plan_research)
    workflow.add_node("researcher", agents.execute_research)
    workflow.add_node("writer", agents.write_report)

    # Add Edges (Linear Flow)
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", END) # End graph here

    # Compile the graph
    return workflow.compile()

# ----------------- 5. PROFESSIONAL PDF GENERATOR (HOXTON STYLE - xhtml2pdf) -----------------

def generate_pdf_report(markdown_content: str, filename: str = "Client_Tax_Report.pdf"):
    """
    Generates a professional, Hoxton-branded PDF from the Markdown report using xhtml2pdf.
    """
    print(f"\n{'='*60}")
    print(f"📄 GENERATING PROFESSIONAL PDF")
    print(f"{'='*60}")
    print(f"📝 Converting Markdown to HTML...")
    
    # 1. Convert Markdown to HTML
    # Use the 'tables' extension for proper table rendering
    html_body = markdown.markdown(markdown_content, extensions=['tables'])
    print(f"   ✓ Markdown converted to HTML ({len(html_body)} chars)")
    
    # 2. HTML Template with Enhanced Hoxton-Branded CSS (SIMPLIFIED - compatible with xhtml2pdf)
    # Note: Removed nested @page rules that caused TypeError in xhtml2pdf
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
                color: #1A4D2E; /* Hoxton Dark Green */
                font-size: 24pt;
                border-bottom: 2px solid #1A4D2E;
                padding-bottom: 10px;
                margin-bottom: 20px;
                margin-top: 0;
            }}
            h2 {{
                color: #1A4D2E;
                font-size: 16pt;
                margin-top: 25px;
                margin-bottom: 10px;
                border-bottom: 1px solid #cccccc;
                padding-bottom: 5px;
            }}
            h3 {{
                color: #34495e;
                font-size: 13pt;
                margin-top: 20px;
                margin-bottom: 5px;
            }}
            /* Table Styling for the "Day Count Scenario" */
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
                font-size: 10pt;
            }}
            th {{
                background-color: #1A4D2E; /* Dark Green Header */
                color: white;
                text-align: left;
                padding: 8px;
                border: 1px solid #dddddd;
            }}
            td {{
                border: 1px solid #dddddd;
                padding: 8px;
                text-align: left;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            blockquote {{
                border-left: 4px solid #1A4D2E;
                margin-left: 0;
                padding-left: 15px;
                color: #555555;
                font-style: italic;
            }}
            p {{
                margin: 10px 0;
            }}
            strong {{
                color: #1A4D2E;
            }}
            ul, ol {{
                margin: 10px 0;
                padding-left: 25px;
            }}
            li {{
                margin: 5px 0;
            }}
            /* Header */
            .header {{
                text-align: right;
                color: #1A4D2E;
                font-size: 9pt;
                margin-bottom: 20px;
                border-bottom: 1px solid #1A4D2E;
                padding-bottom: 5px;
            }}
            /* Footer */
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

    # 3. Generate PDF
    print(f"🎨 Applying Hoxton Tax branding and styling...")
    print(f"📊 Rendering PDF with xhtml2pdf...")
    
    with open(filename, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_template, dest=pdf_file)

    if pisa_status.err:
        print(f"\n❌ PDF generation failed!")
        print(f"   Error: {pisa_status.err}")
        return f"PDF generation failed: {pisa_status.err}"
    else:
        abs_path = os.path.abspath(filename)
        file_size = os.path.getsize(filename) / 1024  # KB
        print(f"\n✅ PDF SUCCESSFULLY GENERATED!")
        print(f"   - Location: {abs_path}")
        print(f"   - File size: {file_size:.1f} KB")
        print(f"   - Format: Professional Hoxton Tax branded A4 PDF")
        return abs_path

# ----------------- 6. EXECUTION -----------------

if __name__ == "__main__":
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + "  🏢 HOXTON TAX LIMITED - AI TAX CONSULTANCY SYSTEM  ".center(58) + "█")
    print("█" + "  Powered by Google Gemini & LangGraph  ".center(58) + "█")
    print("█" + " "*58 + "█")
    print("█"*60 + "\n")
    
    # Example Transcript
    transcript_input = """
    Advisor: Hi Simon, good to speak again. We need to finalize your move plan.
    Simon: Yes. I'm definitely moving to Saudi Arabia (KSA) on September 1st. 
    Advisor: Okay. And the family?
    Simon: My wife Suong is staying in our London home for another year for the kids' school.
    Advisor: That makes the "Main Residence" test tricky. What about the pension?
    Simon: I have £1.2m in a UK SIPP. I want to withdraw it all once I'm resident in KSA. 
    I heard the tax treaty Article 18 says it's taxable only in KSA, which is 0% tax. Can you confirm?
    Advisor: I'll check the treaty. Any other UK ties?
    Simon: I'll come back to the UK for maybe 45 days a year to visit Suong.
    """

    print(f"📋 Transcript loaded: {len(transcript_input)} characters")
    print(f"🏗️  Building LangGraph workflow...")
    app = build_tax_app()
    
    print(f"🚀 Starting agent pipeline...\n")
    result = app.invoke({"transcript": transcript_input})
    
    print("\n\n" + "█"*60)
    print("█" + "  MARKDOWN REPORT PREVIEW  ".center(58) + "█")
    print("█"*60 + "\n")
    
    # Ensure we have a string for the report
    report_content = result["final_report_md"]
    if isinstance(report_content, list):
        print("⚠️  Warning: Report content is a list, extracting text...")
        report_content = report_content[0]['text'] if report_content and 'text' in report_content[0] else str(report_content)
    
    # Preview first 1000 characters
    preview_length = min(1000, len(report_content))
    print(report_content[:preview_length])
    if len(report_content) > preview_length:
        print(f"\n[...truncated {len(report_content) - preview_length} more characters...]")

    # Generate the PDF outside the graph flow, as originally designed
    pdf_path = generate_pdf_report(report_content, "Simon_Tax_Report.pdf")

    print("\n" + "█"*60)
    print("█" + "  PROCESS COMPLETE  ".center(58) + "█")
    print("█"*60)
    print(f"\n✅ All tasks completed successfully!")
    print(f"📂 PDF saved to: {pdf_path}\n")