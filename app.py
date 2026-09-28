import os
import json
import secrets
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash

from database import init_db, get_db_connection
from ai_verifier import GeMBidVerifier
from sample_generator import generate_sample_bids

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32)
CORS(app, supports_credentials=True)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
SAMPLE_FOLDER = os.path.join(os.path.dirname(__file__), 'sample_bids')
ALLOWED_EXTENSIONS = {'pdf', 'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize DB & generate sample bids on startup
init_db()
generate_sample_bids()

verifier = GeMBidVerifier()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

# ---------------------------------------------------------
# AUTHENTICATION ENDPOINTS (ADMIN & VENDOR)
# ---------------------------------------------------------
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"status": "error", "message": "Username and password are required."}), 400

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()

    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({"status": "error", "message": "Invalid username or password."}), 401

    session['user_id'] = user['id']
    session['username'] = user['username']
    session['name'] = user['name']
    session['role'] = user['role']
    session['organization'] = user['organization']

    user_info = {
        "id": user['id'],
        "username": user['username'],
        "name": user['name'],
        "role": user['role'],
        "organization": user['organization']
    }

    return jsonify({"status": "success", "message": f"Welcome back, {user['name']}!", "user": user_info})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"status": "success", "message": "Logged out successfully."})

@app.route('/api/me', methods=['GET'])
def get_current_user():
    if 'user_id' not in session:
        return jsonify({"status": "error", "authenticated": False, "user": None})

    user_info = {
        "id": session.get('user_id'),
        "username": session.get('username'),
        "name": session.get('name'),
        "role": session.get('role'),
        "organization": session.get('organization')
    }
    return jsonify({"status": "success", "authenticated": True, "user": user_info})

# ---------------------------------------------------------
# TENDERS ENDPOINTS
# ---------------------------------------------------------
@app.route('/api/tenders', methods=['GET'])
def get_tenders():
    conn = get_db_connection()
    tenders = conn.execute('SELECT * FROM tenders ORDER BY id DESC').fetchall()
    conn.close()

    result = []
    for t in tenders:
        t_dict = dict(t)
        try:
            t_dict['required_certs'] = json.loads(t_dict['required_certs'])
        except Exception:
            t_dict['required_certs'] = []
        result.append(t_dict)

    return jsonify({"status": "success", "tenders": result})

@app.route('/api/tenders/<int:tender_id>', methods=['GET'])
def get_tender_detail(tender_id):
    conn = get_db_connection()
    tender = conn.execute('SELECT * FROM tenders WHERE id = ?', (tender_id,)).fetchone()
    conn.close()

    if not tender:
        return jsonify({"status": "error", "message": "Tender not found"}), 404

    t_dict = dict(tender)
    try:
        t_dict['required_certs'] = json.loads(t_dict['required_certs'])
    except Exception:
        t_dict['required_certs'] = []

    return jsonify({"status": "success", "tender": t_dict})

@app.route('/api/tenders', methods=['POST'])
def create_tender():
    data = request.json or {}
    tender_ref = data.get('tender_ref', f"GEM/2026/B/{datetime.now().strftime('%M%S%f')[:6]}")
    title = data.get('title', '').strip()
    department = data.get('department', '').strip()
    min_turnover_lakhs = float(data.get('min_turnover_lakhs', 0))
    min_experience_years = int(data.get('min_experience_years', 0))
    min_mii_percent = float(data.get('min_mii_percent', 50.0))
    required_certs = data.get('required_certs', [])
    emd_amount = float(data.get('emd_amount', 0))
    emd_exemption_allowed = 1 if data.get('emd_exemption_allowed', True) else 0
    anti_blacklisting_required = 1 if data.get('anti_blacklisting_required', True) else 0
    closing_date = data.get('closing_date', '2026-12-31')

    if not title or not department:
        return jsonify({"status": "error", "message": "Tender Title and Department are required."}), 400

    certs_json = json.dumps(required_certs if isinstance(required_certs, list) else [c.strip() for c in required_certs.split(',')])
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO tenders (tender_ref, title, department, min_turnover_lakhs, min_experience_years, min_mii_percent, required_certs, emd_amount, emd_exemption_allowed, anti_blacklisting_required, closing_date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tender_ref, title, department, min_turnover_lakhs, min_experience_years, min_mii_percent, certs_json, emd_amount, emd_exemption_allowed, anti_blacklisting_required, closing_date, now))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return jsonify({"status": "success", "tender_id": new_id, "message": "GeM Tender created successfully!"}), 201
    except Exception as e:
        conn.close()
        return jsonify({"status": "error", "message": f"Failed to create tender: {str(e)}"}), 500

# ---------------------------------------------------------
# VERIFICATION & SUBMISSION ENDPOINTS
# ---------------------------------------------------------
@app.route('/api/verify-bid', methods=['POST'])
def verify_bid_endpoint():
    tender_id = request.form.get('tender_id')
    vendor_name = request.form.get('vendor_name', 'Unknown Vendor').strip()
    vendor_gstin = request.form.get('vendor_gstin', 'UNSPECIFIED_GSTIN').strip()

    if not tender_id:
        return jsonify({"status": "error", "message": "Target Tender ID is required"}), 400

    conn = get_db_connection()
    tender = conn.execute('SELECT * FROM tenders WHERE id = ?', (tender_id,)).fetchone()
    if not tender:
        conn.close()
        return jsonify({"status": "error", "message": "Tender not found"}), 404

    tender_data = dict(tender)

    if 'bid_file' not in request.files:
        conn.close()
        return jsonify({"status": "error", "message": "No bid document file uploaded"}), 400

    file = request.files['bid_file']
    if file.filename == '' or not allowed_file(file.filename):
        conn.close()
        return jsonify({"status": "error", "message": "Invalid file format. Please upload PDF or TXT document."}), 400

    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
    saved_filename = timestamp + filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
    file.save(file_path)

    # Execute AI Verification Engine
    res = verifier.verify_bid(tender_data, file_path)

    # Save verification result to Database
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bid_submissions (tender_id, vendor_name, vendor_gstin, filename, compliance_score, status, risk_level, verified_at, summary_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (tender_id, vendor_name, vendor_gstin, saved_filename, res['compliance_score'], res['status'], res['risk_level'], now, res['summary_notes']))

    bid_id = cursor.lastrowid

    for c in res['clauses']:
        cursor.execute('''
            INSERT INTO compliance_results (bid_id, clause_name, required_value, extracted_value, status, confidence, evidence_snippet, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (bid_id, c['clause_name'], c['required_value'], c['extracted_value'], c['status'], c['confidence'], c['evidence_snippet'], c['remarks']))

    conn.commit()
    conn.close()

    res['submission_id'] = bid_id
    res['vendor_name'] = vendor_name
    res['tender_ref'] = tender_data['tender_ref']
    res['verified_at'] = now

    return jsonify({"status": "success", "result": res})

@app.route('/api/submissions', methods=['GET'])
def get_submissions():
    tender_id = request.args.get('tender_id')
    conn = get_db_connection()

    if tender_id:
        query = '''
            SELECT s.*, t.tender_ref, t.title as tender_title
            FROM bid_submissions s
            JOIN tenders t ON s.tender_id = t.id
            WHERE s.tender_id = ?
            ORDER BY s.id DESC
        '''
        submissions = conn.execute(query, (tender_id,)).fetchall()
    else:
        query = '''
            SELECT s.*, t.tender_ref, t.title as tender_title
            FROM bid_submissions s
            JOIN tenders t ON s.tender_id = t.id
            ORDER BY s.id DESC
        '''
        submissions = conn.execute(query).fetchall()

    conn.close()
    return jsonify({"status": "success", "submissions": [dict(s) for s in submissions]})

@app.route('/api/submissions/<int:submission_id>', methods=['GET'])
def get_submission_detail(submission_id):
    conn = get_db_connection()
    sub_query = '''
        SELECT s.*, t.tender_ref, t.title as tender_title, t.department, t.min_turnover_lakhs, t.min_experience_years, t.min_mii_percent, t.required_certs
        FROM bid_submissions s
        JOIN tenders t ON s.tender_id = t.id
        WHERE s.id = ?
    '''
    sub = conn.execute(sub_query, (submission_id,)).fetchone()
    if not sub:
        conn.close()
        return jsonify({"status": "error", "message": "Submission not found"}), 404

    clauses = conn.execute('SELECT * FROM compliance_results WHERE bid_id = ? ORDER BY id ASC', (submission_id,)).fetchall()
    conn.close()

    sub_dict = dict(sub)
    try:
        sub_dict['required_certs'] = json.loads(sub_dict['required_certs'])
    except Exception:
        sub_dict['required_certs'] = []

    return jsonify({
        "status": "success",
        "submission": sub_dict,
        "compliance_matrix": [dict(c) for c in clauses]
    })

# ---------------------------------------------------------
# VENDOR PRE-CHECK PORTAL (INSTANT PRE-SUBMISSION SCAN)
# ---------------------------------------------------------
@app.route('/api/vendor-precheck', methods=['POST'])
def vendor_precheck():
    tender_id = request.form.get('tender_id')
    raw_text = request.form.get('raw_text', '').strip()

    if not tender_id:
        return jsonify({"status": "error", "message": "Target Tender selection is required."}), 400

    conn = get_db_connection()
    tender = conn.execute('SELECT * FROM tenders WHERE id = ?', (tender_id,)).fetchone()
    conn.close()

    if not tender:
        return jsonify({"status": "error", "message": "Selected Tender does not exist."}), 404

    tender_data = dict(tender)

    temp_path = None
    if 'bid_file' in request.files and request.files['bid_file'].filename != '':
        file = request.files['bid_file']
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'precheck_' + filename)
        file.save(temp_path)
    elif raw_text:
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'precheck_temp_text.txt')
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(raw_text)
    else:
        return jsonify({"status": "error", "message": "Please upload a document file or paste your technical bid text."}), 400

    res = verifier.verify_bid(tender_data, temp_path)

    # Clean up temp file
    if temp_path and os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except Exception:
            pass

    return jsonify({"status": "success", "result": res})

# ---------------------------------------------------------
# SAMPLE BIDS & DEMO LOADER / DOWNLOAD
# ---------------------------------------------------------
@app.route('/api/sample-bids/download/<filename>', methods=['GET'])
def download_sample_bid(filename):
    """Download sample bid PDF/TXT files for testing."""
    return send_from_directory(SAMPLE_FOLDER, filename, as_attachment=True)

@app.route('/api/sample-bids/load/<sample_key>', methods=['POST'])
def load_sample_bid(sample_key):
    conn = get_db_connection()
    tender = conn.execute('SELECT * FROM tenders ORDER BY id ASC LIMIT 1').fetchone()
    conn.close()

    if not tender:
        return jsonify({"status": "error", "message": "No active tenders available."}), 400

    tender_data = dict(tender)
    
    if sample_key == 'compliant':
        filename = 'sample_bid_compliant.pdf'
        v_name = 'Apex Tech Systems Pvt Ltd'
        v_gst = '07AAAAA0000A1Z5'
    elif sample_key == 'failing':
        filename = 'sample_bid_non_compliant.pdf'
        v_name = 'Global Imports & Systems LLC'
        v_gst = '27BBBBB1111B2Z2'
    else:
        filename = 'sample_bid_vendor_precheck.txt'
        v_name = 'ElectroCraft Systems'
        v_gst = '33CCCCC2222C3Z3'

    filepath = os.path.join(SAMPLE_FOLDER, filename)
    if not os.path.exists(filepath):
        filepath = os.path.splitext(filepath)[0] + '.txt'

    res = verifier.verify_bid(tender_data, filepath)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO bid_submissions (tender_id, vendor_name, vendor_gstin, filename, compliance_score, status, risk_level, verified_at, summary_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (tender_data['id'], v_name, v_gst, filename, res['compliance_score'], res['status'], res['risk_level'], now, res['summary_notes']))

    bid_id = cursor.lastrowid

    for c in res['clauses']:
        cursor.execute('''
            INSERT INTO compliance_results (bid_id, clause_name, required_value, extracted_value, status, confidence, evidence_snippet, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (bid_id, c['clause_name'], c['required_value'], c['extracted_value'], c['status'], c['confidence'], c['evidence_snippet'], c['remarks']))

    conn.commit()
    conn.close()

    res['submission_id'] = bid_id
    res['vendor_name'] = v_name
    res['tender_ref'] = tender_data['tender_ref']
    res['verified_at'] = now

    return jsonify({"status": "success", "result": res})

# ---------------------------------------------------------
# ANALYTICS ENDPOINT
# ---------------------------------------------------------
@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    conn = get_db_connection()
    total_tenders = conn.execute('SELECT COUNT(*) FROM tenders').fetchone()[0]
    total_bids = conn.execute('SELECT COUNT(*) FROM bid_submissions').fetchone()[0]
    qualified_bids = conn.execute('SELECT COUNT(*) FROM bid_submissions WHERE status = "QUALIFIED"').fetchone()[0]
    disqualified_bids = conn.execute('SELECT COUNT(*) FROM bid_submissions WHERE status = "DISQUALIFIED"').fetchone()[0]
    avg_score_row = conn.execute('SELECT AVG(compliance_score) FROM bid_submissions').fetchone()[0]
    conn.close()

    avg_score = round(avg_score_row, 1) if avg_score_row else 0.0
    pass_rate = round((qualified_bids / total_bids * 100), 1) if total_bids > 0 else 0.0
    time_saved_hours = round(total_bids * 4.5, 1)

    return jsonify({
        "status": "success",
        "analytics": {
            "total_tenders": total_tenders,
            "total_bids": total_bids,
            "qualified_bids": qualified_bids,
            "disqualified_bids": disqualified_bids,
            "pass_rate": pass_rate,
            "avg_compliance_score": avg_score,
            "time_saved_hours": time_saved_hours
        }
    })

if __name__ == '__main__':
    print("Starting GeM AI Bid Compliance Verification Platform on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=os.environ.get('FLASK_DEBUG') == '1')
