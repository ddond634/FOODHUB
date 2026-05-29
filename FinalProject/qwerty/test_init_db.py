import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from server import app, init_db

with app.app_context():
    print("Running init_db()...")
    init_db()
    print("✅ Done!")
    
# Now check tables
import sqlite3
conn = sqlite3.connect('hub.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f'\nTables created: {len(tables)}')
for table in tables:
    print(f'  - {table[0]}')
conn.close()
