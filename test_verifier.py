import os
from database import init_db, get_db_connection
from ai_verifier import GeMBidVerifier
from sample_generator import generate_sample_bids

def test_full_pipeline():
    print("--- 1. Testing Database & Seed Data ---")
    init_db()
    conn = get_db_connection()
    tenders = conn.execute('SELECT * FROM tenders').fetchall()
    print(f"Seeded Tenders Count: {len(tenders)}")
    assert len(tenders) >= 2, "Expected at least 2 tenders"

    tender_1 = dict(tenders[0])
    print(f"Tender 1 Ref: {tender_1['tender_ref']} | Title: {tender_1['title']}")

    print("\n--- 2. Testing Sample Bid Document Generation ---")
    generate_sample_bids()
    sample_dir = os.path.join(os.path.dirname(__file__), 'sample_bids')
    compliant_path = os.path.join(sample_dir, 'sample_bid_compliant.pdf')
    if not os.path.exists(compliant_path):
        compliant_path = os.path.join(sample_dir, 'sample_bid_compliant.txt')
    
    failing_path = os.path.join(sample_dir, 'sample_bid_non_compliant.pdf')
    if not os.path.exists(failing_path):
        failing_path = os.path.join(sample_dir, 'sample_bid_non_compliant.txt')

    print(f"Compliant path exists: {os.path.exists(compliant_path)}")
    print(f"Failing path exists: {os.path.exists(failing_path)}")

    print("\n--- 3. Testing AI Verification Engine on Compliant Bid ---")
    verifier = GeMBidVerifier()
    res_compliant = verifier.verify_bid(tender_1, compliant_path)
    print(f"Compliant Bid Score: {res_compliant['compliance_score']}% | Status: {res_compliant['status']} | Risk: {res_compliant['risk_level']}")
    assert res_compliant['status'] == 'QUALIFIED', f"Expected QUALIFIED, got {res_compliant['status']}"

    print("\n--- 4. Testing AI Verification Engine on Non-Compliant Bid ---")
    res_failing = verifier.verify_bid(tender_1, failing_path)
    print(f"Failing Bid Score: {res_failing['compliance_score']}% | Status: {res_failing['status']} | Risk: {res_failing['risk_level']}")
    assert res_failing['status'] == 'DISQUALIFIED', f"Expected DISQUALIFIED, got {res_failing['status']}"

    conn.close()
    print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_full_pipeline()
