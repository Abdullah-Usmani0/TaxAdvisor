"""
Test PDF generation with different approaches
This file tests various PDF generation methods to find the best one
"""

import markdown
from xhtml2pdf import pisa
import os

# Sample markdown content (similar to what we generate)
test_markdown = """
# Tax Residency & Planning Report for Simon

**Date:** 26 May 2024  
**Prepared by:** Hoxton Tax Limited

## Executive Summary

Simon, a current UK tax resident, intends to relocate to Saudi Arabia (KSA) with the specific financial goal of withdrawing his entire £1.2m UK Self-Invested Personal Pension (SIPP) free of UK income tax.

Our analysis confirms that this strategy is legally viable under the **UK-Saudi Arabia Double Taxation Convention**, specifically **Article 18**.

## UK Statutory Residence Test (SRT) Analysis

### Day Count Scenario Table

| Number of Ties | Maximum Days in UK | Status |
|----------------|-------------------|---------|
| 0 Ties | Up to 182 days | Non-Resident |
| 1 Tie | Up to 120 days | Non-Resident |
| 2 Ties | **Up to 90 days** | **Likely Scenario** |
| 3 Ties | Up to 45 days | Scenario if Wife stays |

## Recommendations

1. **Apply for NT Tax Code**
2. **Strict Day Counting**
3. **Five-Year Horizon**

## Disclaimer

"This report has been compiled based on UK tax legislation and guidance in force at the time of writing. Any tax laws, rates and allowances quoted are subject to change."
"""

def test_xhtml2pdf_simple():
    """Test xhtml2pdf with SIMPLIFIED CSS (no complex @page rules)"""
    print("\n" + "="*60)
    print("TEST 1: xhtml2pdf with Simplified CSS")
    print("="*60)
    
    try:
        html_body = markdown.markdown(test_markdown, extensions=['tables'])
        
        # Simplified CSS - removed problematic @page nested rules
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
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                    font-size: 10pt;
                }}
                th {{
                    background-color: #1A4D2E;
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
        
        filename = "test_simple_xhtml2pdf.pdf"
        with open(filename, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_template, dest=pdf_file)
        
        if pisa_status.err:
            print(f"❌ FAILED: {pisa_status.err}")
            return False
        else:
            file_size = os.path.getsize(filename) / 1024
            print(f"✅ SUCCESS!")
            print(f"   - File: {os.path.abspath(filename)}")
            print(f"   - Size: {file_size:.1f} KB")
            return True
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_reportlab():
    """Test ReportLab (requires: pip install reportlab)"""
    print("\n" + "="*60)
    print("TEST 2: ReportLab (Professional PDF Library)")
    print("="*60)
    
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        
        filename = "test_reportlab.pdf"
        doc = SimpleDocTemplate(filename, pagesize=A4, 
                               leftMargin=2.5*cm, rightMargin=2.5*cm,
                               topMargin=2.5*cm, bottomMargin=2.5*cm)
        
        # Container for the 'Flowable' objects
        story = []
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1A4D2E'),
            spaceAfter=20,
            borderPadding=10,
            borderColor=colors.HexColor('#1A4D2E'),
            borderWidth=2,
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1A4D2E'),
            spaceBefore=25,
            spaceAfter=10,
        )
        
        # Add header
        header = Paragraph("<b>Hoxton Tax Limited</b> | Client Tax Report", styles['Normal'])
        story.append(header)
        story.append(Spacer(1, 0.5*cm))
        
        # Add title
        title = Paragraph("Tax Residency & Planning Report for Simon", title_style)
        story.append(title)
        
        # Add content
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Paragraph("Simon, a current UK tax resident, intends to relocate to Saudi Arabia...", styles['Normal']))
        story.append(Spacer(1, 0.3*cm))
        
        # Add table
        story.append(Paragraph("Day Count Scenario Table", heading_style))
        data = [
            ['Number of Ties', 'Maximum Days in UK', 'Status'],
            ['0 Ties', 'Up to 182 days', 'Non-Resident'],
            ['1 Tie', 'Up to 120 days', 'Non-Resident'],
            ['2 Ties', 'Up to 90 days', 'Likely Scenario'],
        ]
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A4D2E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        story.append(table)
        
        # Build PDF
        doc.build(story)
        
        file_size = os.path.getsize(filename) / 1024
        print(f"✅ SUCCESS!")
        print(f"   - File: {os.path.abspath(filename)}")
        print(f"   - Size: {file_size:.1f} KB")
        print(f"   - Note: ReportLab offers excellent control and quality!")
        return True
        
    except ImportError:
        print(f"⚠️  SKIPPED: ReportLab not installed")
        print(f"   Install with: pip install reportlab")
        return None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "█"*60)
    print("█" + "  PDF GENERATION TESTING SUITE  ".center(58) + "█")
    print("█"*60)
    
    results = {}
    
    # Test 1: xhtml2pdf with simplified CSS
    results['xhtml2pdf_simple'] = test_xhtml2pdf_simple()
    
    # Test 2: ReportLab
    results['reportlab'] = test_reportlab()
    
    # Summary
    print("\n" + "█"*60)
    print("█" + "  TEST RESULTS SUMMARY  ".center(58) + "█")
    print("█"*60)
    
    for test_name, result in results.items():
        if result is True:
            print(f"✅ {test_name}: PASSED")
        elif result is False:
            print(f"❌ {test_name}: FAILED")
        elif result is None:
            print(f"⚠️  {test_name}: SKIPPED")
    
    print("\n" + "="*60)
    print("RECOMMENDATION:")
    if results['xhtml2pdf_simple']:
        print("✅ Use xhtml2pdf with SIMPLIFIED CSS (already installed)")
        print("   This will work immediately with your existing setup!")
    else:
        print("⚠️  Consider installing ReportLab for better PDF quality")
        print("   Run: pip install reportlab")
    print("="*60 + "\n")

