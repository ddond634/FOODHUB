import sys
import os
from datetime import datetime

# Ensure project root on path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.server import get_db, app, DB_ENGINE
from werkzeug.security import generate_password_hash

def seed_admin(email=None, password=None, first_name='Admin', last_name='User'):
    email = email or os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    password = password or os.environ.get('ADMIN_PASSWORD', 'Admin123!')
    with app.app_context():
        db = get_db(); cur = db.cursor()
        try:
            # Check if exists
            if DB_ENGINE == 'mysql':
                cur.execute("SELECT id FROM users WHERE email=%s;", (email,))
            else:
                cur.execute("SELECT id FROM users WHERE email=?;", (email,))
            row = cur.fetchone()
            if row:
                print(f"[INFO] Admin already exists: {email} (id={row['id']})")
                return row['id']
            pw_hash = generate_password_hash(password)
            now = datetime.utcnow().isoformat()
            # Create admin user, verified
            if DB_ENGINE == 'mysql':
                cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,is_verified,created_at) VALUES (%s,%s,%s,%s,%s,1,%s);",
                            (email, pw_hash, first_name, last_name, 'admin', now))
            else:
                cur.execute("INSERT INTO users (email,password_hash,first_name,last_name,role,is_verified,created_at) VALUES (?,?,?,?,?,1,?);",
                            (email, pw_hash, first_name, last_name, 'admin', now))
            admin_id = cur.lastrowid
            db.commit()
            print(f"[OK] Admin created: {email} (id={admin_id})")
            return admin_id
        finally:
            try: cur.close()
            except: pass

if __name__ == '__main__':
    seed_admin()
