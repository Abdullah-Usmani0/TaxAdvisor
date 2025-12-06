import os
import operator
from typing import List, Annotated, TypedDict, Optional, Dict
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ----------------- LIBRARIES -----------------
# pip install langgraph langchain-google-genai langchain-community tavily-python markdown xhtml2pdf python-dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, END
import markdown
from xhtml2pdf import pisa

# ----------------- CONFIGURATION -----------------
# Ensure API keys are set
if not os.getenv("TAVILY_API_KEY"):
    print("Warning: TAVILY_API_KEY not found in environment variables.")
if not os.getenv("GOOGLE_API_KEY"):
    print("Warning: GOOGLE_API_KEY not found in environment variables.")

LLM_MODEL = "gemini-3-pro-preview"

# ----------------- 1. DATA MODELS (The "Brain") -----------------

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
    transcript: str                  # Input: The conversation text
    profile: ClientProfile           # Extracted data
    research_plan: ResearchPlan      # What we intend to search
    research_context: str            # Raw data found from Tavily
    final_report: str                # Output: The Markdown report

# ----------------- 3. NODES (The Agents) -----------------

class TaxConsultancyAgents:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(model=LLM_MODEL, temperature=0)
        # Tavily is set to 'advanced' depth to find specific clauses inside documents
        self.search_tool = TavilySearchResults(
            max_results=5, 
            search_depth="advanced", 
            include_raw_content=True
        )

    # --- NODE 1: EXTRACTOR ---
    def extract_profile(self, state: TaxState):
        print(f"--- [1] EXTRACTING PROFILE ---")
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert Tax Clerk. Extract the client profile strictly based on the transcript."),
            ("human", "{transcript}")
        ])
        
        # Force structured output using Pydantic
        extractor = prompt | self.llm.with_structured_output(ClientProfile)
        profile = extractor.invoke({"transcript": state["transcript"]})
        
        return {"profile": profile}

    # --- NODE 2: PLANNER ---
    def plan_research(self, state: TaxState):
        print(f"--- [2] PLANNING RESEARCH ---")
        profile = state["profile"]
        
        # Format profile data to avoid template variable conflicts
        profile_str = profile.model_dump_json()
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Senior Tax Partner. Plan the research for this client. Focus on Statutory Residence Tests, Double Tax Treaties, and specific local tax laws (e.g., UK, KSA, Italy)."),
            ("human", "Client Profile: {profile_data}")
        ])
        
        planner = prompt | self.llm.with_structured_output(ResearchPlan)
        plan = planner.invoke({"profile_data": profile_str})
        
        return {"research_plan": plan}

    # --- NODE 3: RESEARCHER (TAVILY) ---
    def execute_research(self, state: TaxState):
        print(f"--- [3] EXECUTING RESEARCH ---")
        plan = state["research_plan"]
        compiled_research = []

        print(f"    > Running {len(plan.queries)} deep searches...")
        
        for query in plan.queries:
            try:
                # Add "current tax year" to ensure freshness
                enhanced_query = f"{query} current tax legislation 2024 2025"
                results = self.search_tool.invoke(enhanced_query)
                
                # Format results for the Writer
                snippet_text = "\n".join([f"- Source: {r['url']}\n  Content: {r['content'][:500]}..." for r in results])
                compiled_research.append(f"### Query: {query}\n{snippet_text}\n")
            except Exception as e:
                print(f"    ! Search failed for '{query}': {e}")

        return {"research_context": "\n".join(compiled_research)}

    # --- NODE 4: WRITER ---
    def write_report(self, state: TaxState):
        print(f"--- [4] WRITING REPORT ---")
        profile = state["profile"]
        context = state["research_context"]

        # This prompt mimics the "Hoxton" style from your documents
        prompt_template = """
        You are a Tax Consultant at 'Hoxton Tax Limited'. Write a comprehensive Tax Report for {client_name}.
        
        STYLE GUIDE:
        - Use professional UK English.
        - Structure: Executive Summary, Premise, Statutory Residence Test Analysis, Double Tax Treaty Analysis, Recommendations, Disclaimer.
        - **Crucial**: You must generate a "Day Count Scenario" table if the Statutory Residence Test is involved.
        - Use the Disclaimer provided below exactly.

        CLIENT DATA:
        {profile_json}

        LEGAL CONTEXT (Use this for citations):
        {context}

        DISCLAIMER TEXT:
        "This report has been compiled based on tax legislation and guidance in force at the time of writing. Any tax laws, rates and allowances quoted are subject to change. We do not accept liability for losses arising from changes in the law."

        OUTPUT FORMAT:
        Markdown.
        """
        
        prompt = ChatPromptTemplate.from_template(prompt_template)
        chain = prompt | self.llm
        
        report = chain.invoke({
            "client_name": profile.client_name,
            "profile_json": profile.model_dump_json(),
            "context": context
        })
        
        return {"final_report": report.content}

# ----------------- 4. GRAPH CONSTRUCTION -----------------

def build_tax_app():
    agents = TaxConsultancyAgents()
    workflow = StateGraph(TaxState)

    # Add Nodes
    workflow.add_node("extractor", agents.extract_profile)
    workflow.add_node("planner", agents.plan_research)
    workflow.add_node("researcher", agents.execute_research)
    workflow.add_node("writer", agents.write_report)

    # Add Edges (Linear Flow for this version)
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", END)

    # Compile the graph
    return workflow.compile()

# ----------------- 5. HELPER FUNCTIONS -----------------

def generate_pdf_report(markdown_content: str, filename: str = "Client_Tax_Report.pdf"):
    """Generates a professional PDF from the Markdown report."""
    print(f"--- GENERATING PDF: {filename} ---")
    
    # Convert Markdown to HTML
    html_body = markdown.markdown(markdown_content, extensions=['tables'])
    
    # HTML Template with Industry Standard CSS
    html_template = f"""
    <html>
    <head>
        <style>
            @page {{
                size: A4;
                margin: 2cm;
            }}
            body {{
                font-family: "Helvetica", "Arial", sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #333333;
            }}
            h1 {{
                color: #2c3e50;
                font-size: 24pt;
                border-bottom: 2px solid #2c3e50;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            h2 {{
                color: #2980b9;
                font-size: 16pt;
                margin-top: 25px;
                margin-bottom: 10px;
            }}
            h3 {{
                color: #34495e;
                font-size: 13pt;
                margin-top: 20px;
                margin-bottom: 5px;
            }}
            p {{
                margin-bottom: 10px;
                text-align: justify;
            }}
            ul, ol {{
                margin-bottom: 10px;
                padding-left: 20px;
            }}
            li {{
                margin-bottom: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 20px;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
                font-weight: bold;
            }}
            .footer {{
                position: fixed;
                bottom: 0;
                width: 100%;
                text-align: center;
                font-size: 9pt;
                color: #7f8c8d;
            }}
            blockquote {{
                border-left: 4px solid #bdc3c7;
                margin-left: 0;
                padding-left: 15px;
                color: #7f8c8d;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        {html_body}
        <div class="footer">
            Hoxton Tax Limited - Confidential Client Report
        </div>
    </body>
    </html>
    """

    # Generate PDF
    with open(filename, "wb") as pdf_file:
        pisa_status = pisa.CreatePDF(html_template, dest=pdf_file)

    if pisa_status.err:
        print("!! PDF generation failed !!")
    else:
        print(f"PDF successfully saved to {os.path.abspath(filename)}")

# ----------------- 6. EXECUTION -----------------

if __name__ == "__main__":
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

    app = build_tax_app()
    
    print("Starting Tax Consultancy Agent Swarm (Gemini 3 Pro Edition)...")
    result = app.invoke({"transcript": transcript_input})
    
    print("\n\n" + "="*50)
    print("FINAL GENERATED REPORT")
    print("="*50)
    print(result["final_report"])

    # Generate the PDF
    generate_pdf_report(result["final_report"], "Simon_Tax_Report.pdf")
