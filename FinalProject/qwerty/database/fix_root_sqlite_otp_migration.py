#!/usr/bin/env python3
"""
Fix migration: add otp_code and is_verified columns to project-root qwerty.db
This script connects to the qwerty.db located at the project root (one level up from this file)
and adds the columns if they're missing.
"""
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(ROOT_DIR, 'qwerty.db')

if not os.path.exists(DB_PATH):
    print(f"Database not found at {DB_PATH}")
    raise SystemExit(1)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cur.execute("PRAGMA table_info(users)")
columns = [r[1] for r in cur.fetchall()]
print("Existing user table columns:", columns)
changed = False

if 'otp_code' not in columns:
    print("Adding otp_code column...")
    cur.execute("ALTER TABLE users ADD COLUMN otp_code TEXT DEFAULT NULL;")
    changed = True
else:
    print("otp_code already present")

if 'is_verified' not in columns:
    print("Adding is_verified column...")
    cur.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER DEFAULT 0;")
    changed = True
else:
    print("is_verified already present")

if changed:
    conn.commit()
    print("Migration applied to", DB_PATH)
else:
    print("No changes needed")

cur.close()
conn.close()
