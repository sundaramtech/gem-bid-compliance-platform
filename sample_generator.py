import os
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), 'sample_bids')

def generate_pdf(filepath, title, content_lines):
    """Generate a clean sample PDF using ReportLab if available, or write a plain text fallback."""
    if REPORTLAB_AVAILABLE:
        try:
            c = canvas.Canvas(filepath, pagesize=letter)
            width, height = letter
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, title)
            c.setLineWidth(1)
            c.line(50, height - 60, width - 50, height - 60)
            
            c.setFont("Helvetica", 10)
            y = height - 85
            for line in content_lines:
                if y < 50:
                    c.showPage()
                    y = height - 50
                    c.setFont("Helvetica", 10)
                
                if line.startswith("---") or line.startswith("=="):
                    c.setLineWidth(0.5)
                    c.line(50, y, width - 50, y)
                    y -= 15
                elif line.isupper() and len(line) < 40:
                    c.setFont("Helvetica-Bold", 11)
                    c.drawString(50, y, line)
                    c.setFont("Helvetica", 10)
                    y -= 16
                else:
                    c.drawString(50, y, line[:100])
                    y -= 14
            c.save()
            return
        except Exception as e:
            print(f"PDF generation failed, falling back to TXT: {e}")

    # Fallback to TXT
    txt_path = os.path.splitext(filepath)[0] + '.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"=== {title} ===\n\n")
        f.write("\n".join(content_lines))

def generate_sample_bids():
    os.makedirs(SAMPLE_DIR, exist_ok=True)

    # 1. Compliant Bid Document
    b1_lines = [
        "TECHNICAL BID SUBMISSION - GOVERNMENT e-MARKETPLACE (GeM)",
        "Tender Reference: GEM/2026/B/984210",
        "Bidder Name: Apex Tech Systems Pvt Ltd",
        "GSTIN: 07AAAAA0000A1Z5 | Corporate Identification: U72200DL2018PTC123456",
        "--------------------------------------------------------------------------------",
        "1. FINANCIAL TURNOVER CERTIFICATE",
        "This is to certify that M/s Apex Tech Systems Pvt Ltd has achieved the following",
        "Annual Financial Turnover in the past 3 financial years as audited by Chartered Accountants:",
        " - FY 2022-23: INR 135.00 Lakhs",
        " - FY 2023-24: INR 148.50 Lakhs",
        " - FY 2024-25: INR 153.00 Lakhs",
        "Average Annual Financial Turnover: INR 145.50 Lakhs (Rupees One Crore Forty Five Lakhs).",
        "--------------------------------------------------------------------------------",
        "2. PAST EXPERIENCE & TECHNICAL CAPABILITY",
        "Apex Tech Systems has over 5 years of experience in supplying enterprise workstations",
        "and AI server compute infrastructure to PSUs and Govt organizations (DRDO, ISRO, BEL).",
        "--------------------------------------------------------------------------------",
        "3. MAKE IN INDIA (MII) LOCAL CONTENT DECLARATION",
        "We hereby declare and affirm that the local content in the offered products is 62.0%",
        "manufactured at our Noida Assembly Facility, meeting Class-I Local Supplier criteria.",
        "--------------------------------------------------------------------------------",
        "4. QUALITY CERTIFICATIONS ATTACHED",
        " - ISO 9001:2015 Quality Management Certificate Registration No: IND-89412 (Valid till Nov 2027)",
        " - ISO 27001:2022 Information Security Certificate Registration No: IS-99120 (Valid till Dec 2028)",
        " - Official OEM Authorization Certificate from Intel Corp attached.",
        "--------------------------------------------------------------------------------",
        "5. EMD EXEMPTION DECLARATION",
        "Claiming EMD Exemption under MSME Policy. Attached valid Udyam Registration Certificate:",
        "Udyam Reg No: UDYAM-DL-03-0012345",
        "--------------------------------------------------------------------------------",
        "6. UNDERTAKING FOR NON-BLACK LISTING",
        "We solemnly affirm on Non-Judicial Stamp paper that Apex Tech Systems has never been blacklisted",
        "or debarred by any Central/State Govt Department, Autonomous Body, or Public Sector Undertaking."
    ]
    generate_pdf(os.path.join(SAMPLE_DIR, 'sample_bid_compliant.pdf'), "TECHNICAL BID - APEX TECH SYSTEMS (FULLY COMPLIANT)", b1_lines)

    # 2. Non-Compliant Bid Document
    b2_lines = [
        "TECHNICAL BID SUBMISSION - GE M TENDER EVALUATION",
        "Tender Reference: GEM/2026/B/984210",
        "Bidder Name: Global Imports & Systems LLC",
        "GSTIN: 27BBBBB1111B2Z2",
        "--------------------------------------------------------------------------------",
        "1. FINANCIAL TURNOVER DECLARATION",
        "Annual financial turnover for the company for FY 2024-25 is INR 1.1 Crore (INR 110.0 Lakhs).",
        "--------------------------------------------------------------------------------",
        "2. COMPANY EXPERIENCE",
        "Company incorporated in 2024 with 2 years of commercial operations in IT supply.",
        "--------------------------------------------------------------------------------",
        "3. LOCAL VALUE ADDITION STATEMENT",
        "Imported components account for 68% of total hardware cost. Local content value addition is 32.0%.",
        "--------------------------------------------------------------------------------",
        "4. CERTIFICATES ATTACHED",
        " - ISO 9001:2015 Quality Certificate attached.",
        " - ISO 27001: Certificate under renewal process (Not attached in bid envelope).",
        "--------------------------------------------------------------------------------",
        "5. EMD DETAILS",
        "Paid EMD amount of INR 75,000 via NEFT UTR No. SBIN9841298412.",
        "--------------------------------------------------------------------------------",
        "6. SELF DECLARATION",
        "Self statement on company letterhead regarding business operations."
    ]
    generate_pdf(os.path.join(SAMPLE_DIR, 'sample_bid_non_compliant.pdf'), "TECHNICAL BID - GLOBAL IMPORTS (NON-COMPLIANT)", b2_lines)

    # Plain text version for quick file picker / copy-paste
    txt_path = os.path.join(SAMPLE_DIR, 'sample_bid_vendor_precheck.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(b1_lines))

if __name__ == '__main__':
    generate_sample_bids()
    print("Sample bids generated successfully!")
