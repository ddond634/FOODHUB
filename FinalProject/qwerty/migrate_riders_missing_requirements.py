#!/usr/bin/env python3
"""
Migration: Add missing_requirements and decline fields to riders table
"""
import pymysql
import sys

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'qwerty',
    'charset': 'utf8mb4'
}

def column_exists(cur, table, column):
    cur.execute("""
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s
    """, (DB_CONFIG['database'], table, column))
    return cur.fetchone()[0] > 0


def run():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor()
        print('\n[1/1] Ensuring riders table has required columns...')

        columns = [
            ("missing_requirements", "TEXT"),
            ("declined_at", "DATETIME"),
            ("declined_by", "INT"),
            ("decline_reason", "TEXT")
        ]

        for name, ctype in columns:
            if not column_exists(cur, 'riders', name):
                print(f"  Adding column {name} {ctype}...")
                if name == 'declined_by':
                    cur.execute(f"ALTER TABLE riders ADD COLUMN {name} {ctype}")
                    conn.commit()
                    # add foreign key
                    try:
                        cur.execute("ALTER TABLE riders ADD CONSTRAINT fk_riders_declined_by FOREIGN KEY (declined_by) REFERENCES users(id) ON DELETE SET NULL")
                        conn.commit()
                    except Exception:
                        # ignore if constraint exists or cannot be added
                        pass
                else:
                    cur.execute(f"ALTER TABLE riders ADD COLUMN {name} {ctype}")
                    conn.commit()
                print(f"    ✓ {name} added")
            else:
                print(f"    ⚠ {name} already exists, skipping")

        cur.close()
        conn.close()
        print('\nMigration complete')
        return True
    except Exception as e:
        print('\nMigration failed:', e)
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    ok = run()
    sys.exit(0 if ok else 1)
