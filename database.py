import sqlite3
import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

DB_FILE = os.path.join(os.path.dirname(__file__), 'gem_compliance.db')

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # 0. Users Table (Role-based auth: ADMIN vs VENDOR)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL, -- ADMIN, VENDOR
            organization TEXT,
            created_at TEXT NOT NULL
        )
    ''')

    # 1. Tenders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_ref TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            department TEXT NOT NULL,
            min_turnover_lakhs REAL NOT NULL,
            min_experience_years INTEGER NOT NULL,
            min_mii_percent REAL NOT NULL,
            required_certs TEXT NOT NULL, -- JSON array string
            emd_amount REAL NOT NULL,
            emd_exemption_allowed INTEGER NOT NULL DEFAULT 1, -- 1=True, 0=False
            anti_blacklisting_required INTEGER NOT NULL DEFAULT 1,
            closing_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # 2. Bid Submissions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bid_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tender_id INTEGER NOT NULL,
            vendor_name TEXT NOT NULL,
            vendor_gstin TEXT NOT NULL,
            filename TEXT NOT NULL,
            compliance_score REAL NOT NULL,
            status TEXT NOT NULL, -- QUALIFIED, DISQUALIFIED, CONDITIONALLY_QUALIFIED, UNDER_REVIEW
            risk_level TEXT NOT NULL, -- LOW, MEDIUM, HIGH
            verified_at TEXT NOT NULL,
            summary_notes TEXT,
            FOREIGN KEY (tender_id) REFERENCES tenders (id) ON DELETE CASCADE
        )
    ''')

    # 3. Compliance Clause Results Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compliance_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bid_id INTEGER NOT NULL,
            clause_name TEXT NOT NULL,
            required_value TEXT NOT NULL,
            extracted_value TEXT NOT NULL,
            status TEXT NOT NULL, -- COMPLIANT, NON_COMPLIANT, WARNING, MANUAL_CHECK
            confidence REAL NOT NULL,
            evidence_snippet TEXT,
            remarks TEXT,
            FOREIGN KEY (bid_id) REFERENCES bid_submissions (id) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    seed_users_data(conn)
    seed_initial_data(conn)
    conn.close()

def seed_users_data(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] > 0:
        return  # Users already seeded

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. Admin Account (Procurement Officer / GeM Buyer)
    admin_pw = generate_password_hash('admin123')
    cursor.execute('''
        INSERT INTO users (username, password_hash, name, role, organization, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('admin', admin_pw, 'Rajesh Sharma (Procurement Officer)', 'ADMIN', 'Ministry of Defence / GeM Portal', now))

    # 2. User / Vendor Account (Supplier / Seller)
    vendor_pw = generate_password_hash('vendor123')
    cursor.execute('''
        INSERT INTO users (username, password_hash, name, role, organization, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('vendor', vendor_pw, 'Apex Tech Bidding Manager', 'VENDOR', 'Apex Tech Systems Pvt Ltd', now))

    conn.commit()

def seed_initial_data(conn):
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM tenders')
    if cursor.fetchone()[0] > 0:
        return  # Data already seeded

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Sample Tender 1
    t1_certs = json.dumps(["ISO 9001:2015", "ISO 27001:2022", "GSTIN", "OEM Authorization"])
    cursor.execute('''
        INSERT INTO tenders (tender_ref, title, department, min_turnover_lakhs, min_experience_years, min_mii_percent, required_certs, emd_amount, emd_exemption_allowed, anti_blacklisting_required, closing_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'GEM/2026/B/984210',
        'Procurement of 500 High-Performance Workstations & GPU Racks',
        'Ministry of Defence / DRDO R&D Centre',
        100.0, 3, 50.0, t1_certs, 75000.0, 1, 1, '2026-10-15', now
    ))
    t1_id = cursor.lastrowid

    # Sample Tender 2
    t2_certs = json.dumps(["ISO 9001:2015", "Cisco Gold Partner Cert", "GSTIN"])
    cursor.execute('''
        INSERT INTO tenders (tender_ref, title, department, min_turnover_lakhs, min_experience_years, min_mii_percent, required_certs, emd_amount, emd_exemption_allowed, anti_blacklisting_required, closing_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'GEM/2026/B/441092',
        'Annual Maintenance Contract (AMC) for Enterprise Network Infrastructure',
        'Ministry of Railways / Northern Zone',
        45.0, 5, 20.0, t2_certs, 25000.0, 1, 1, '2026-10-30', now
    ))
    t2_id = cursor.lastrowid

    # Seed Sample Bid Submission 1 (Fully Compliant Vendor for Tender 1)
    cursor.execute('''
        INSERT INTO bid_submissions (tender_id, vendor_name, vendor_gstin, filename, compliance_score, status, risk_level, verified_at, summary_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        t1_id, 'Apex Tech Systems Pvt Ltd', '07AAAAA0000A1Z5', 'apex_tech_bid_compliant.pdf',
        96.5, 'QUALIFIED', 'LOW', now,
        'All mandatory terms & conditions satisfied with verified audited turnover and valid MII declaration of 62%.'
    ))
    b1_id = cursor.lastrowid

    b1_clauses = [
        ('Annual Financial Turnover', '>= ₹100.00 Lakhs', '₹145.50 Lakhs (Audited 2024-25)', 'COMPLIANT', 0.98, 'Extract: "Average Turnover for past 3 consecutive years is INR 145.50 Lakhs certified by CA."', 'Verified with attached CA Certificate.'),
        ('Past Experience Criteria', '>= 3 Years', '5 Years relevant supply history', 'COMPLIANT', 0.95, 'Extract: "Company has successfully supplied workstations to ISRO and BEL since 2021."', 'Purchase orders verified.'),
        ('Make in India (MII) Content %', '>= 50.0%', '62.0% Local Content Self-Declaration', 'COMPLIANT', 0.99, 'Extract: "We hereby certify local value addition of 62% manufactured at Noida unit."', 'MII Form 1 verified.'),
        ('Mandatory Quality Certifications', 'ISO 9001:2015, ISO 27001:2022', 'ISO 9001:2015 (Exp: 2027), ISO 27001:2022 (Exp: 2028)', 'COMPLIANT', 0.97, 'Extract: "ISO 9001:2015 Registration No. IND-89412 valid through Nov 2027."', 'Certificates valid.'),
        ('EMD & Fee Exemption', '₹75,000 or MSME Udyam Exemption', 'MSME Udyam Exempt (Reg: UDYAM-DL-03-0012345)', 'COMPLIANT', 0.99, 'Extract: "Claiming EMD exemption under MSME Policy. Attached valid Udyam cert."', 'Exemption valid under GeM terms.'),
        ('Anti-Blacklisting Declaration', 'Mandatory Self-Declaration', 'Submitted on ₹100 Stamp Paper', 'COMPLIANT', 0.96, 'Extract: "We solemnly affirm that Apex Tech has never been blacklisted by any PSU/Govt."', 'Notarized affidavit detected.')
    ]

    for c in b1_clauses:
        cursor.execute('''
            INSERT INTO compliance_results (bid_id, clause_name, required_value, extracted_value, status, confidence, evidence_snippet, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (b1_id, c[0], c[1], c[2], c[3], c[4], c[5], c[6]))

    # Seed Sample Bid Submission 2 (Disqualified Vendor for Tender 1)
    cursor.execute('''
        INSERT INTO bid_submissions (tender_id, vendor_name, vendor_gstin, filename, compliance_score, status, risk_level, verified_at, summary_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        t1_id, 'Global Imports & Systems LLC', '27BBBBB1111B2Z2', 'global_imports_bid_failing.pdf',
        42.0, 'DISQUALIFIED', 'HIGH', now,
        'Critical non-compliance detected: Local MII Content is 32% (below 50% threshold) and ISO 27001 certificate is missing.'
    ))
    b2_id = cursor.lastrowid

    b2_clauses = [
        ('Annual Financial Turnover', '>= ₹100.00 Lakhs', '₹110.00 Lakhs', 'COMPLIANT', 0.92, 'Extract: "Annual turnover for 2024 is INR 1.1 Crore."', 'Turnover criteria met.'),
        ('Past Experience Criteria', '>= 3 Years', '2 Years experience', 'WARNING', 0.88, 'Extract: "Incorporated in 2023 with 2 years of commercial operation."', 'Below recommended 3 years threshold.'),
        ('Make in India (MII) Content %', '>= 50.0%', '32.0% Local Content (Non-Compliant)', 'NON_COMPLIANT', 0.99, 'Extract: "Imported components account for 68%. Local content value addition is 32%."', 'Failed mandatory Class-I local supplier threshold (50%).'),
        ('Mandatory Quality Certifications', 'ISO 9001:2015, ISO 27001:2022', 'ISO 9001:2015 only (ISO 27001 Missing)', 'NON_COMPLIANT', 0.90, 'Extract: "Attached ISO 9001 cert. ISO 27001 under renewal process."', 'ISO 27001 missing in technical envelope.'),
        ('EMD & Fee Exemption', '₹75,000 or MSME Udyam Exemption', 'EMD NEFT Receipt of ₹75,000 attached', 'COMPLIANT', 0.98, 'Extract: "UTR No. SBIN9841298412 for INR 75,000 paid to GeM portal."', 'EMD verified.'),
        ('Anti-Blacklisting Declaration', 'Mandatory Self-Declaration', 'Plain paper undertaking attached', 'WARNING', 0.82, 'Extract: "Self statement on company letterhead."', 'Tender required non-judicial stamp paper affidavit.')
    ]

    for c in b2_clauses:
        cursor.execute('''
            INSERT INTO compliance_results (bid_id, clause_name, required_value, extracted_value, status, confidence, evidence_snippet, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (b2_id, c[0], c[1], c[2], c[3], c[4], c[5], c[6]))

    conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized with users table and GeM seed data!")
