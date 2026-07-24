-- BIST LOB Analysis PostgreSQL şeması.
-- Önce hedef veritabanını oluşturun, sonra bu dosyayı o veritabanında çalıştırın.

CREATE TABLE IF NOT EXISTS analysis_runs (
    id              BIGSERIAL PRIMARY KEY,
    pcap_path       TEXT NOT NULL,
    snapshot_every  BIGINT NOT NULL,
    status          VARCHAR(16) NOT NULL DEFAULT 'running',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    CHECK (snapshot_every > 0),
    CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS order_book_directory (
    order_book_id   INTEGER PRIMARY KEY,
    symbol          VARCHAR(32) NOT NULL,
    financial_product SMALLINT,
    price_decimals  SMALLINT NOT NULL DEFAULT 2,
    isin            VARCHAR(12),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS price_table_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    run_id          BIGINT REFERENCES analysis_runs(id),
    sequence_number BIGINT NOT NULL,
    event_ts_sec    BIGINT,
    event_ts_nsec   BIGINT,
    order_book_id   INTEGER NOT NULL,
    symbol          VARCHAR(32) NOT NULL,
    best_bid        DOUBLE PRECISION,
    best_ask        DOUBLE PRECISION,
    mid_price       DOUBLE PRECISION,
    spread          DOUBLE PRECISION,
    bid_price_1  DOUBLE PRECISION, bid_qty_1  BIGINT,
    bid_price_2  DOUBLE PRECISION, bid_qty_2  BIGINT,
    bid_price_3  DOUBLE PRECISION, bid_qty_3  BIGINT,
    bid_price_4  DOUBLE PRECISION, bid_qty_4  BIGINT,
    bid_price_5  DOUBLE PRECISION, bid_qty_5  BIGINT,
    bid_price_6  DOUBLE PRECISION, bid_qty_6  BIGINT,
    bid_price_7  DOUBLE PRECISION, bid_qty_7  BIGINT,
    bid_price_8  DOUBLE PRECISION, bid_qty_8  BIGINT,
    bid_price_9  DOUBLE PRECISION, bid_qty_9  BIGINT,
    bid_price_10 DOUBLE PRECISION, bid_qty_10 BIGINT,
    ask_price_1  DOUBLE PRECISION, ask_qty_1  BIGINT,
    ask_price_2  DOUBLE PRECISION, ask_qty_2  BIGINT,
    ask_price_3  DOUBLE PRECISION, ask_qty_3  BIGINT,
    ask_price_4  DOUBLE PRECISION, ask_qty_4  BIGINT,
    ask_price_5  DOUBLE PRECISION, ask_qty_5  BIGINT,
    ask_price_6  DOUBLE PRECISION, ask_qty_6  BIGINT,
    ask_price_7  DOUBLE PRECISION, ask_qty_7  BIGINT,
    ask_price_8  DOUBLE PRECISION, ask_qty_8  BIGINT,
    ask_price_9  DOUBLE PRECISION, ask_qty_9  BIGINT,
    ask_price_10 DOUBLE PRECISION, ask_qty_10 BIGINT,
    captured_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Eski kurulumlarla uyumluluk: mevcut tabloya run_id eklenir.
ALTER TABLE price_table_snapshots
    ADD COLUMN IF NOT EXISTS run_id BIGINT REFERENCES analysis_runs(id);

CREATE TABLE IF NOT EXISTS order_events (
    id              BIGSERIAL PRIMARY KEY,
    run_id          BIGINT REFERENCES analysis_runs(id),
    sequence_number BIGINT NOT NULL,
    event_ts_sec    BIGINT,
    event_ts_nsec   BIGINT,
    order_book_id   INTEGER NOT NULL,
    symbol          VARCHAR(32) NOT NULL,
    event_type      CHAR(1) NOT NULL,
    side            CHAR(1),
    price           DOUBLE PRECISION,
    quantity        BIGINT,
    order_id        BIGINT,
    captured_at     TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE order_events
    ADD COLUMN IF NOT EXISTS run_id BIGINT REFERENCES analysis_runs(id);

CREATE INDEX IF NOT EXISTS idx_pts_sequence ON price_table_snapshots(sequence_number);
CREATE INDEX IF NOT EXISTS idx_pts_symbol_seq ON price_table_snapshots(symbol, sequence_number);
CREATE INDEX IF NOT EXISTS idx_pts_event_ts ON price_table_snapshots(event_ts_sec, event_ts_nsec);
CREATE INDEX IF NOT EXISTS idx_pts_run_symbol_seq ON price_table_snapshots(run_id, symbol, sequence_number);
CREATE INDEX IF NOT EXISTS idx_pts_run_order_book_seq ON price_table_snapshots(run_id, order_book_id, sequence_number);
CREATE UNIQUE INDEX IF NOT EXISTS uq_pts_run_symbol_seq
    ON price_table_snapshots(run_id, symbol, sequence_number)
    WHERE run_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_oe_run_symbol_seq ON order_events(run_id, symbol, sequence_number);
CREATE INDEX IF NOT EXISTS idx_oe_run_order_book_seq ON order_events(run_id, order_book_id, sequence_number);
