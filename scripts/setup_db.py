"""BIST LOB şemasını hedef PostgreSQL veritabanına güvenli biçimde uygular."""
import os
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("psycopg2 gerekli: pip install -r requirements.txt")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
CONN = os.environ.get("BIST_DB_CONN", "dbname=bist_lob_db")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    print(f"PostgreSQL şeması uygulanıyor: {SCHEMA_PATH}")
    with psycopg2.connect(CONN) as conn:
        conn.set_client_encoding("UTF8")
        with conn.cursor() as cur:
            cur.execute(schema)
    print("[OK] Tablolar ve indeksler hazır.")


if __name__ == "__main__":
    main()
