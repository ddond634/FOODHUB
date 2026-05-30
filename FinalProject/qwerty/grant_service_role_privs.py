#!/usr/bin/env python3
"""Grant INSERT/SELECT privileges on app tables to the `service_role` DB role.
This connects directly to the Supabase Postgres using the connection string in .env.
"""
import os
import sys
from dotenv import load_dotenv

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, '.env'))

DB_URL = os.getenv('Supabase_Postgresql') or os.getenv('SUPABASE_POSTGRESQL') or os.getenv('SUPABASE_DB_URL')
if not DB_URL:
    print('No Postgres connection string found in .env (Supabase_Postgresql)')
    sys.exit(1)

try:
    import psycopg2
except ImportError:
    print('psycopg2 not installed. Please run: pip install psycopg2-binary')
    sys.exit(1)

tables = ['users','sellers','products','cart_items','wishlist','product_variation_options','orders','order_items']
grants = []
for t in tables:
    grants.append(f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.{t} TO service_role;")
    grants.append(f"GRANT USAGE, SELECT ON SEQUENCE public.{t}_id_seq TO service_role;")

print('Connecting to Postgres...')
conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()
for g in grants:
    try:
        print('Executing:', g)
        cur.execute(g)
    except Exception as e:
        print('Failed:', e)

cur.close()
conn.close()
print('Done.')
