import os
import sys
import psycopg2

CONN_STR = os.environ.get("BIST_DB_CONN", "dbname=bist_lob_db host=localhost port=5432 user=postgres")

def main():
    print(f"Connecting to database with: {CONN_STR}")
    try:
        conn = psycopg2.connect(CONN_STR)
        print("[OK] Successfully connected to bist_lob_db.")
        conn.close()
    except Exception as e:
        print(f"[INFO] Could not connect directly to bist_lob_db ({e}). Trying default 'postgres' db...")
        try:
            pg_conn = psycopg2.connect("dbname=postgres host=localhost port=5432 user=postgres")
            pg_conn.autocommit = True
            with pg_conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = 'bist_lob_db'")
                if not cur.fetchone():
                    print("[INFO] Creating database 'bist_lob_db'...")
                    cur.execute("CREATE DATABASE bist_lob_db")
                    print("[OK] Database 'bist_lob_db' created successfully.")
                else:
                    print("[OK] Database 'bist_lob_db' already exists.")
            pg_conn.close()
        except Exception as e2:
            print(f"[ERROR] Failed to connect to PostgreSQL: {e2}")
            sys.exit(1)

if __name__ == "__main__":
    main()
