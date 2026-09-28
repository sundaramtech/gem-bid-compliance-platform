from database import init_db, get_db_connection
from werkzeug.security import check_password_hash

def test_auth_system():
    print("--- 1. Testing User DB Table & Password Hashes ---")
    init_db()
    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users').fetchall()
    print(f"Total Users Seeded: {len(users)}")
    assert len(users) >= 2, "Expected at least 2 default users"

    admin_user = conn.execute('SELECT * FROM users WHERE username = "admin"').fetchone()
    vendor_user = conn.execute('SELECT * FROM users WHERE username = "vendor"').fetchone()

    assert admin_user is not None, "Admin user missing"
    assert vendor_user is not None, "Vendor user missing"

    print(f"Admin User Found: {admin_user['username']} | Role: {admin_user['role']}")
    print(f"Vendor User Found: {vendor_user['username']} | Role: {vendor_user['role']}")

    assert check_password_hash(admin_user['password_hash'], 'admin123'), "Admin password validation failed"
    assert check_password_hash(vendor_user['password_hash'], 'vendor123'), "Vendor password validation failed"
    assert not check_password_hash(admin_user['password_hash'], 'wrongpassword'), "Wrong password check failed"

    conn.close()
    print("\nALL AUTHENTICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == '__main__':
    test_auth_system()
