"""Setup PostgreSQL schema for BIST LOB project."""
import os
import sys

try:
    import psycopg2
except ImportError:
    print("psycopg2 gerekli: pip install psycopg2-binary")
    sys.exit(1)

CONN = os.environ.get(
    "BIST_DB_CONN",
    "dbname=bist_lob_db user=postgres password=erenberke host=localhost port=5432",
)

DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS order_book_directory (
        order_book_id INTEGER PRIMARY KEY,
        symbol VARCHAR(32) NOT NULL,
        financial_product SMALLINT,
        price_decimals SMALLINT NOT NULL DEFAULT 2,
        isin VARCHAR(12),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS price_table_snapshots (
        id BIGSERIAL PRIMARY KEY,
        sequence_number BIGINT NOT NULL,
        event_ts_sec BIGINT,
        event_ts_nsec BIGINT,
        order_book_id INTEGER NOT NULL,
        symbol VARCHAR(32) NOT NULL,
        best_bid DOUBLE PRECISION,
        best_ask DOUBLE PRECISION,
        mid_price DOUBLE PRECISION,
        spread DOUBLE PRECISION,
        bid_price_1 DOUBLE PRECISION, bid_qty_1 BIGINT,
        bid_price_2 DOUBLE PRECISION, bid_qty_2 BIGINT,
        bid_price_3 DOUBLE PRECISION, bid_qty_3 BIGINT,
        bid_price_4 DOUBLE PRECISION, bid_qty_4 BIGINT,
        bid_price_5 DOUBLE PRECISION, bid_qty_5 BIGINT,
        bid_price_6 DOUBLE PRECISION, bid_qty_6 BIGINT,
        bid_price_7 DOUBLE PRECISION, bid_qty_7 BIGINT,
        bid_price_8 DOUBLE PRECISION, bid_qty_8 BIGINT,
        bid_price_9 DOUBLE PRECISION, bid_qty_9 BIGINT,
        bid_price_10 DOUBLE PRECISION, bid_qty_10 BIGINT,
        ask_price_1 DOUBLE PRECISION, ask_qty_1 BIGINT,
        ask_price_2 DOUBLE PRECISION, ask_qty_2 BIGINT,
        ask_price_3 DOUBLE PRECISION, ask_qty_3 BIGINT,
        ask_price_4 DOUBLE PRECISION, ask_qty_4 BIGINT,
        ask_price_5 DOUBLE PRECISION, ask_qty_5 BIGINT,
        ask_price_6 DOUBLE PRECISION, ask_qty_6 BIGINT,
        ask_price_7 DOUBLE PRECISION, ask_qty_7 BIGINT,
        ask_price_8 DOUBLE PRECISION, ask_qty_8 BIGINT,
        ask_price_9 DOUBLE PRECISION, ask_qty_9 BIGINT,
        ask_price_10 DOUBLE PRECISION, ask_qty_10 BIGINT,
        captured_at TIMESTAMPTZ DEFAULT NOW()
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_pts_sequence ON price_table_snapshots(sequence_number);",
    "CREATE INDEX IF NOT EXISTS idx_pts_symbol ON price_table_snapshots(symbol);",
    "CREATE INDEX IF NOT EXISTS idx_pts_order_book_id ON price_table_snapshots(order_book_id);",
    "CREATE INDEX IF NOT EXISTS idx_pts_event_ts ON price_table_snapshots(event_ts_sec, event_ts_nsec);",
]


def main():
    print("PostgreSQL semasi olusturuluyor...")
    conn = psycopg2.connect(CONN)
    conn.autocommit = True
    cur = conn.cursor()
    for stmt in DDL_STATEMENTS:
        cur.execute(stmt)
    cur.close()
    conn.close()
    print("[OK] Tablolar hazir.")


if __name__ == "__main__":
    main()
