import sqlite3
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(script_dir, 'hub.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    print(f"  - {table[0]}")
    
# Check sellers table structure if it exists
if ('sellers',) in tables:
    cursor.execute("PRAGMA table_info(sellers)")
    columns = cursor.fetchall()
    print("\nSellers table columns:")
    for col in columns:
        print(f"  - {col[1]} ({col[2]})")

conn.close()
