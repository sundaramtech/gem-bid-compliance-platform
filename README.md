# AI-Powered Integrated Bid Compliance Verification Platform for GeM Procurement

A local demonstration prototype for checking technical bids against manually entered GeM tender requirements. It uses PDF text extraction, keyword matching, and rules to produce a reviewable compliance report. Results require human verification.

---

## 🌟 Problem Solved

In public procurement on GeM, evaluating technical bids manually takes weeks:
1. **High Turn-Around Time (TAT)**: Evaluators must manually inspect 20–100+ page technical bid PDFs.
2. **Human Oversight & Disqualification Risk**: Missed non-compliances (expired ISO certs, turnover below threshold, low Make in India local content %) lead to improper awards or unfair disqualifications.
3. **Lack of Clause-by-Clause Evidence**: Difficult to maintain transparent audit trails for legal and regulatory compliance.

### How GeM AI Solves It:
- **Instant AI Extraction**: Automatically parses financial turnover (Lakhs/Crores), experience years, Make in India (MII) local content %, ISO 9001/27001 certificates, EMD exemption status, and anti-blacklisting affidavits.
- **Clause-by-Clause Compliance Matrix**: Displays side-by-side requirement vs extracted value with exact document evidence snippets and confidence ratings.
- **Vendor Pre-Check Portal**: Bidders can test their bid document before official submission to fix red flags early.
- **Audit History & Executive Analytics**: Comprehensive officer dashboard tracking total bids scanned, pass rates, risk ratings, and hours saved.

---

## 🛠️ Technology Stack

- **Frontend**: Vanilla HTML5 + CSS3 (Modern GeM Dark Slate & Glassmorphism Theme) + Vanilla JavaScript (ES6 Modules, Fetch API, FontAwesome Icons).
- **Backend / API**: Python 3 (Flask framework + Flask-CORS).
- **Database**: SQLite 3 (created locally with sample data on first run).
- **ML / AI Engine**: Python `pypdf` + Regular Expression Pattern Extractor + NLP Keyword Similarity Engine + Rule-Based Clause Matcher.

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10+ installed on your system.

### 1. Setup Project Directory & Environment
```bash
# Navigate to project directory
cd gem_bid_compliance_platform

# Install dependencies
python -m venv .venv
# Activate: Windows .venv\Scripts\activate  |  macOS/Linux source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Run Application
```bash
python app.py
```
The server will start at: `http://127.0.0.1:5000`

The local demo seeds two accounts: `admin` / `admin123` and `vendor` / `vendor123`. Set `FLASK_SECRET_KEY` to a long random value to keep browser sessions across restarts. These demo accounts and API routes are **not suitable for public deployment**; add server-side authorization, secure user setup, and deployment hardening first. Keep real procurement and vendor documents out of this prototype. The application does not perform OCR on scanned PDFs; upload selectable-text PDFs or TXT files.

---

## 📡 REST API Documentation

| Method | Endpoint | Description | Request | Response |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/api/tenders` | Fetch all GeM tenders | None | `{status, tenders: []}` |
| `POST` | `/api/tenders` | Create new GeM tender | `JSON {tender_ref, title, department, min_turnover_lakhs, ...}` | `{status, tender_id}` |
| `POST` | `/api/verify-bid` | Upload bid PDF/TXT & execute AI verification | `FormData (tender_id, vendor_name, bid_file)` | `{status, result: {compliance_score, status, clauses: []}}` |
| `POST` | `/api/sample-bids/load/<key>` | Run instant verification on pre-seeded sample bids | None (`key` = `compliant` / `failing`) | `{status, result: {...}}` |
| `POST` | `/api/vendor-precheck` | Instant pre-submission health scan for bidders | `FormData (tender_id, raw_text, bid_file)` | `{status, result: {...}}` |
| `GET` | `/api/submissions` | List all verified bid submissions | `?tender_id=1` (optional) | `{status, submissions: []}` |
| `GET` | `/api/submissions/<id>` | Get complete compliance matrix for a bid | None | `{status, submission, compliance_matrix: []}` |
| `GET` | `/api/analytics` | Fetch executive dashboard KPIs | None | `{status, analytics: {...}}` |

---

## 🎯 Demo Walkthrough Instructions

1. **Open Web Browser**: Open `http://127.0.0.1:5000`.
2. **Executive Dashboard**: Review live KPI cards (Active Tenders, Bids Evaluated, Technical Pass Rate, Officer Hours Saved).
3. **1-Click Hackathon Demo**:
   - Click the **"Demo Compliant Bid"** button on the top navbar or dashboard card.
   - Watch the real-time AI scanning pulse animation.
   - Observe the calculated compliance result and evidence for the sample document.
   - Click **"Test Failing Bid"** to compare the result with a document containing missing or insufficient evidence.
4. **AI Bid Verifier**:
   - Go to **AI Bid Verifier** tab.
   - Select a GeM Tender, enter vendor details, and drag-and-drop any custom PDF/TXT file or select a file from `sample_bids/`.
   - Click **"Execute AI Verification"** to view clause-by-clause extractions and evidence snippets.
5. **Vendor Pre-Check**:
   - Go to **Vendor Pre-Check** tab.
   - Paste draft technical bid text or upload a draft file to get actionable recommendations before bidding.
6. **Audit History & Report Export**:
   - View all evaluated bids in the **Audit History** tab.
   - Click **"Print / PDF Report"** to generate a printable compliance verification certificate.

