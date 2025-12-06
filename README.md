# 🏢 Hoxton Tax Limited - AI Tax Consultancy System

An intelligent multi-agent tax consultancy system powered by Google Gemini and LangGraph that automatically analyzes tax residency scenarios and generates professional PDF reports.

## 🌟 Features

- **🔍 Intelligent Profile Extraction**: Automatically extracts client information from conversation transcripts
- **📋 Research Planning**: AI-powered research strategy generation focusing on Statutory Residence Tests and Double Tax Treaties
- **🔎 Legal Research**: Deep web search using Tavily API for current tax legislation (2024-2025)
- **✍️ Report Generation**: Comprehensive, professionally formatted tax reports with detailed analysis
- **📄 PDF Export**: Beautiful, branded PDF reports with Hoxton Tax styling
- **📊 Detailed Logging**: Step-by-step visibility into the entire process

## 🎯 Use Case

This system is designed for tax consultants and advisors who need to:
- Analyze cross-border tax residency scenarios
- Understand Statutory Residence Test (SRT) implications
- Review Double Tax Treaty (DTT) provisions
- Generate detailed client reports with legal backing

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Gemini API Key
- Tavily API Key (for web research)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/Abdullah-Usmani0/TaxAdvisor.git
cd TaxAdvisor
```

2. **Create a virtual environment**
```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install langgraph langchain-google-genai langchain-community tavily-python markdown xhtml2pdf python-dotenv
```

4. **Set up environment variables**

Create a `.env` file in the project root:
```env
GOOGLE_API_KEY=your_google_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

### Get API Keys

- **Google Gemini API**: [Get API Key](https://makersuite.google.com/app/apikey)
- **Tavily API**: [Get API Key](https://tavily.com/)

## 💻 Usage

Run the main agent:

```bash
python agent2.py
```

The system will:
1. 🔍 Extract client profile from the transcript
2. 📋 Plan research strategy
3. 🔎 Execute deep web searches for tax legislation
4. ✍️ Generate comprehensive tax report
5. 📄 Create professional PDF output

### Example Output

```
████████████████████████████████████████████████████████████
█       🏢 HOXTON TAX LIMITED - AI TAX CONSULTANCY SYSTEM   █
█            Powered by Google Gemini & LangGraph           █
████████████████████████████████████████████████████████████

============================================================
🔍 [STEP 1/4] EXTRACTING CLIENT PROFILE
============================================================
📝 Processing transcript (487 characters)...
🤖 Calling Gemini API for structured extraction...
✅ Profile extracted successfully!
   - Client Name: Simon
   - Current Tax Residency: United Kingdom
   - Target Tax Residency: Saudi Arabia (KSA)
   ...
```

## 📁 Project Structure

```
TaxAdvisor/
├── agent2.py                    # Main application (enhanced with logging)
├── agent.py                     # Previous version (reference)
├── test_pdf_generation.py       # PDF generation testing suite
├── .env                         # Environment variables (create this)
├── README.md                    # This file
└── requirements.txt             # Python dependencies (optional)
```

## 🔧 Configuration

### Changing the LLM Model

In `agent2.py`, modify the configuration section:

```python
# Use gemini-2.5-pro if GOOGLE_API_KEY is not set
# Use gemini-3-pro-preview if GOOGLE_API_KEY is set
LLM_MODEL = "gemini-2.5-pro"  # or "gemini-3-pro-preview"
```

### Customizing the Research

Modify the research planner prompt in `TaxConsultancyAgents.plan_research()`:

```python
("system", "You are a Senior Tax Partner. Plan the research for this client. 
Focus on Statutory Residence Tests, Double Tax Treaties, and specific local 
tax laws (e.g., UK, KSA, Italy).")
```

### PDF Styling

Customize the Hoxton Tax branding in `generate_pdf_report()`:

- **Primary Color**: `#1A4D2E` (Dark Green)
- **Font**: Helvetica/Arial
- **Page Size**: A4
- **Margins**: 2.5cm

## 📊 Report Structure

Generated reports include:

1. **Executive Summary**: High-level overview of the tax situation
2. **Premise (Client Situation)**: Detailed client circumstances
3. **UK Statutory Residence Test (SRT) Analysis**: 
   - Day count scenarios
   - Tie analysis
   - Residency determination
4. **Double Tax Treaty (DTT) Analysis**: 
   - Article-by-article review
   - Tie-breaker clauses
   - Tax implications
5. **Recommendations and Planning Summary**: Actionable advice
6. **Disclaimer**: Professional liability disclaimer

## 🧪 Testing PDF Generation

Test different PDF generation approaches:

```bash
python test_pdf_generation.py
```

This will:
- Test xhtml2pdf with simplified CSS
- Test ReportLab (if installed)
- Generate sample PDFs for comparison

## 🛠️ Troubleshooting

### Common Issues

**1. Module Not Found Errors**
```bash
pip install --upgrade pip
pip install langgraph langchain-google-genai langchain-community tavily-python markdown xhtml2pdf python-dotenv
```

**2. API Key Errors**
- Ensure `.env` file exists in project root
- Verify API keys are valid and active
- Check for typos in environment variable names

**3. PDF Generation Errors**
- The system uses simplified CSS for xhtml2pdf compatibility
- If issues persist, try: `pip install --upgrade xhtml2pdf`

**4. Model Not Found (gemini-3-pro)**
- The code defaults to `gemini-2.5-pro` if GOOGLE_API_KEY is missing
- Check your API key has access to the specified model

## 📝 Dependencies

- `langgraph` - Orchestration framework for multi-agent systems
- `langchain-google-genai` - Google Gemini LLM integration
- `langchain-community` - Community tools (Tavily search)
- `tavily-python` - Advanced web search API
- `markdown` - Markdown to HTML conversion
- `xhtml2pdf` - PDF generation
- `python-dotenv` - Environment variable management

## 🔐 Security Notes

- Never commit your `.env` file to version control
- Keep API keys secure and rotate them regularly
- The `.gitignore` file excludes sensitive files

## 📄 License

This project is for educational and professional use. Ensure compliance with:
- Google Gemini API Terms of Service
- Tavily API Terms of Service
- Relevant tax advisory regulations in your jurisdiction

## 🤝 Contributing

This is a private repository. For issues or improvements, please contact the repository owner.

## 👤 Author

**Abdullah Usmani**
- GitHub: [@Abdullah-Usmani0](https://github.com/Abdullah-Usmani0)

## 🙏 Acknowledgments

- **Google Gemini** for powerful LLM capabilities
- **LangGraph** for multi-agent orchestration
- **Tavily** for advanced web search
- **Hoxton Tax Limited** for the use case and branding inspiration

---

**⚠️ Disclaimer**: This system is a tool to assist tax professionals. All generated reports should be reviewed by qualified tax advisors before being provided to clients. The system does not constitute professional tax advice.

