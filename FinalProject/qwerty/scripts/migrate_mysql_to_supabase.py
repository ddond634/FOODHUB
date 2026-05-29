"""Migrate rows from a MySQL database into Supabase (Postgres) via the REST API.

Usage:
  python -m scripts.migrate_mysql_to_supabase --execute  # actually perform inserts
  python -m scripts.migrate_mysql_to_supabase              # dry-run: lists tables and counts

Notes:
- Requires `pymysql` and `requests` (already in .local_packages used by this workspace).
- Uses Supabase Service Role key from `Supabase_Service_role_key` in .env for full insert privileges.
"""
from dotenv import load_dotenv
import os
import json
import argparse
from time import sleep

load_dotenv('.env')

try:
    import pymysql
except Exception:
    pymysql = None

try:
    import requests
except Exception:
    requests = None


def get_mysql_conn():
    if pymysql is None:
        raise RuntimeError('pymysql is not installed')

    cfg = {
        'host': os.getenv('DB_HOST', '127.0.0.1'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASS', ''),
        'db': os.getenv('DB_NAME', 'qwerty'),
        'port': int(os.getenv('DB_PORT', '3306')),
        'cursorclass': pymysql.cursors.DictCursor,
        'charset': 'utf8mb4'
    }
    return pymysql.connect(**cfg)


def get_supabase_config():
    url = os.getenv('Supabase_URL')
    srv_key = os.getenv('Supabase_Service_role_key')
    if not url or not srv_key:
        raise RuntimeError('Supabase_URL and Supabase_Service_role_key must be set in .env')
    rest_url = url.rstrip('/') + '/rest/v1'
    headers = {
        'apikey': srv_key,
        'Authorization': f'Bearer {srv_key}',
        'Content-Type': 'application/json',
        'Prefer': 'return=representation'
    }
    return rest_url, headers


def list_tables(conn):
    with conn.cursor() as cur:
        cur.execute('SHOW TABLES')
        rows = cur.fetchall()
        # result shape depends on MySQL server version; extract first value
        tables = []
        for r in rows:
            if isinstance(r, dict):
                tables.append(list(r.values())[0])
            else:
                tables.append(r[0])
        return tables


def fetch_batch(conn, table, offset, limit=1000):
    with conn.cursor() as cur:
        cur.execute(f'SELECT * FROM `{table}` LIMIT %s OFFSET %s', (limit, offset))
        return cur.fetchall()


def normalize_row(row):
    # Convert non-json-serializable types (e.g., bytes, datetime) to strings
    for k, v in list(row.items()):
        if v is None:
            continue
        if hasattr(v, 'isoformat'):
            row[k] = v.isoformat()
        elif isinstance(v, (bytes, bytearray)):
            row[k] = v.decode('utf-8', errors='ignore')
        elif not isinstance(v, (str, int, float, bool)):
            row[k] = str(v)
    return row


def migrate_table(conn, rest_url, headers, table, execute=False):
    offset = 0
    batch = fetch_batch(conn, table, offset, limit=1000)
    total = 0
    errors = 0
    while batch:
        prepared = [normalize_row(r) for r in batch]
        if execute:
            resp = requests.post(f'{rest_url}/{table}', headers=headers, data=json.dumps(prepared))
            if resp.status_code not in (200, 201):
                print(f'Insert failed for table {table} offset {offset}:', resp.status_code, resp.text)
                errors += 1
            else:
                created = len(resp.json()) if resp.text else 0
                total += created
        else:
            print(f'[dry-run] would insert {len(prepared)} rows into {table} (offset {offset})')

        offset += len(batch)
        batch = fetch_batch(conn, table, offset, limit=1000)
        # be polite
        sleep(0.01)

    return total, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='Actually perform inserts into Supabase')
    parser.add_argument('--tables', nargs='*', help='Optional list of tables to migrate')
    args = parser.parse_args()

    if requests is None:
        print('requests is not installed')
        return 2

    try:
        conn = get_mysql_conn()
    except Exception as e:
        print('Failed to connect to MySQL:', e)
        return 3

    try:
        rest_url, headers = get_supabase_config()
    except Exception as e:
        print('Supabase config error:', e)
        conn.close()
        return 4

    try:
        tables = args.tables or list_tables(conn)
        # Filter out internal MySQL tables
        tables = [t for t in tables if t.lower() not in ('schema_migrations', 'migrations')]
        print('Tables to migrate:', tables)

        grand_total = 0
        grand_errors = 0
        for t in tables:
            print('Migrating table:', t)
            created, errors = migrate_table(conn, rest_url, headers, t, execute=args.execute)
            grand_total += created
            grand_errors += errors

        print('Done. created rows:', grand_total, 'errors:', grand_errors)
        return 0
    finally:
        conn.close()


if __name__ == '__main__':
    raise SystemExit(main())
