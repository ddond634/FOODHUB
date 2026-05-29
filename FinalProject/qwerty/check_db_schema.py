import sqlite3
import os

# Check both possible database locations
db_paths = ['qwerty.db', 'database/hub.db']
db_path = None

for path in db_paths:
    if os.path.exists(path):
        db_path = path
        print(f'Found database: {path}')
        break

if not db_path:
    print('No database file found!')
    exit(1)

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all tables
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f'\nTables: {[t[0] for t in tables]}')
    
    # Get users table columns
    if 'users' in [t[0] for t in tables]:
        cursor.execute('PRAGMA table_info(users)')
        cols = cursor.fetchall()
        print(f'\nUsers table columns ({len(cols)} total):')
        for col in cols:
            print(f'  - {col[1]} ({col[2]})')
        
        # Check for specific columns we need
        col_names = [col[1] for col in cols]
        required_cols = ['middle_name', 'suffix', 'address_line1', 'address_line2', 'city', 'province', 'region', 'postal_code']
        print(f'\nRequired columns check:')
        for req_col in required_cols:
            exists = req_col in col_names
            print(f'  - {req_col}: {"✅ EXISTS" if exists else "❌ MISSING"}')
    
    conn.close()
else:
    print('Database file not found!')

