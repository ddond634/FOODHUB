from dotenv import load_dotenv
import os

def main():
    load_dotenv('.env')
    db_url = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL')
    if not db_url:
        print('SUPABASE_DB_URL is not set in .env; please set it to your Supabase Postgres URL')
        return 2

    try:
        import psycopg2
        import psycopg2.extras
    except Exception as e:
        print('psycopg2 is not installed or failed to import:', e)
        return 3

    try:
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        cur.execute('SELECT current_database(), version()')
        row = cur.fetchone()
        print('Connected to database:', row[0])
        print('Server version:', row[1])
        cur.close()
        conn.close()
        return 0
    except Exception as e:
        print('Failed to connect to Supabase/Postgres:', e)
        return 4

if __name__ == '__main__':
    raise SystemExit(main())
