"""
BIST Pay / Vadeli sembol cifti analizi.
DB'den fiyat tablolarini ceker, iliskiyi raporlar, CSV ve grafik uretir.
"""
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError as e:
    raise SystemExit("psycopg2 gerekli: pip install psycopg2-binary") from e

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "symbol_pairs.json"
OUTPUT_DIR = ROOT / "output"
REPORTS_DIR = OUTPUT_DIR / "reports"
CHARTS_DIR = OUTPUT_DIR / "charts"

CONN = os.environ.get(
    "BIST_DB_CONN",
    "dbname=bist_lob_db user=postgres password=erenberke host=localhost port=5432",
)


def load_pairs():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)["pairs"]


def fetch_snapshots(conn, symbol: str) -> pd.DataFrame:
    query = """
        SELECT sequence_number, event_ts_sec, event_ts_nsec, order_book_id, symbol,
               best_bid, best_ask, mid_price, spread, captured_at
        FROM price_table_snapshots
        WHERE symbol = %s AND mid_price > 0
        ORDER BY sequence_number
    """
    return pd.read_sql(query, conn, params=(symbol,))


def analyze_pair(conn, pair: dict) -> pd.DataFrame:
    spot_sym = pair["spot"]
    fut_sym = pair["future"]
    label = pair["label"]

    spot = fetch_snapshots(conn, spot_sym)
    fut = fetch_snapshots(conn, fut_sym)

    if spot.empty or fut.empty:
        print(f"[UYARI] {label}: yeterli veri yok (spot={len(spot)}, future={len(fut)})")
        return pd.DataFrame()

    spot = spot.rename(columns={
        "mid_price": "spot_mid", "best_bid": "spot_bid", "best_ask": "spot_ask",
        "spread": "spot_spread", "sequence_number": "seq",
    })
    fut = fut.rename(columns={
        "mid_price": "future_mid", "best_bid": "future_bid", "best_ask": "future_ask",
        "spread": "future_spread",
    })

    merged = pd.merge(
        spot[["seq", "event_ts_sec", "event_ts_nsec", "order_book_id", "spot_mid", "spot_bid", "spot_ask", "spot_spread"]],
        fut[["seq", "future_mid", "future_bid", "future_ask", "future_spread"]],
        on="seq",
        how="inner",
    )

    if merged.empty:
        merged = pd.merge_asof(
            spot.sort_values("seq"),
            fut.sort_values("seq"),
            on="seq",
            direction="nearest",
            tolerance=5000,
        )

    merged["pair"] = label
    merged["spot_symbol"] = spot_sym
    merged["future_symbol"] = fut_sym
    merged["basis"] = merged["future_mid"] - merged["spot_mid"]
    merged["basis_pct"] = (merged["basis"] / merged["spot_mid"]) * 100.0
    merged["spot_momentum"] = merged["spot_mid"].pct_change().fillna(0) * 100.0
    merged["future_momentum"] = merged["future_mid"].pct_change().fillna(0) * 100.0
    merged["momentum_spread"] = merged["future_momentum"] - merged["spot_momentum"]

    return merged


def save_report(df: pd.DataFrame, label: str):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"{label}_analysis.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  CSV: {path}")


def save_charts(df: pd.DataFrame, label: str):
    if df.empty:
        return
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(f"{label}: Pay vs Vadeli Analizi", fontsize=14)

    axes[0].plot(df["seq"], df["spot_mid"], label="Pay (Spot)", alpha=0.8)
    axes[0].plot(df["seq"], df["future_mid"], label="Vadeli", alpha=0.8)
    axes[0].set_ylabel("Mid Price (TL)")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(df["seq"], df["basis"], color="purple", alpha=0.8)
    axes[1].axhline(0, color="gray", linestyle="--", linewidth=0.8)
    axes[1].set_ylabel("Basis (Vadeli - Pay)")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(df["seq"], df["spot_momentum"], label="Pay Momentum %", alpha=0.7)
    axes[2].plot(df["seq"], df["future_momentum"], label="Vadeli Momentum %", alpha=0.7)
    axes[2].set_ylabel("Momentum (%)")
    axes[2].set_xlabel("Sequence Number")
    axes[2].legend()
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    chart_path = CHARTS_DIR / f"{label}_analysis.png"
    plt.savefig(chart_path, dpi=150)
    plt.close()
    print(f"  Grafik: {chart_path}")


def query_demo(conn):
    """Ornek sorgular - zaman, sequence, order_book_id, sembol."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    print("\n--- Ornek DB Sorgulari ---")

    cur.execute("""
        SELECT symbol, COUNT(*) AS snapshot_count,
               MIN(sequence_number) AS min_seq, MAX(sequence_number) AS max_seq
        FROM price_table_snapshots
        GROUP BY symbol ORDER BY symbol
    """)
    rows = cur.fetchall()
    if rows:
        print("\nSembol bazli ozet:")
        for r in rows:
            print(f"  {r['symbol']}: {r['snapshot_count']} snapshot, seq {r['min_seq']}-{r['max_seq']}")
    else:
        print("\n[UYARI] price_table_snapshots tablosu bos. Once lob_engine calistirin.")

    cur.execute("""
        SELECT sequence_number, order_book_id, symbol, mid_price, spread
        FROM price_table_snapshots
        WHERE symbol = 'THYAO.E'
        ORDER BY sequence_number DESC LIMIT 3
    """)
    rows = cur.fetchall()
    if rows:
        print("\nTHYAO.E son 3 snapshot (sequence sorgusu):")
        for r in rows:
            print(f"  seq={r['sequence_number']} ob_id={r['order_book_id']} mid={r['mid_price']:.2f} spread={r['spread']:.4f}")

    cur.close()


def main():
    pairs = load_pairs()
    print(f"=== BIST Pay/Vadeli Analiz ({len(pairs)} cift) ===")

    conn = psycopg2.connect(CONN)

    summary_rows = []
    for pair in pairs:
        label = pair["label"]
        print(f"\nAnaliz: {pair['spot']} / {pair['future']}")
        df = analyze_pair(conn, pair)
        if df.empty:
            continue
        save_report(df, label)
        save_charts(df, label)
        summary_rows.append({
            "pair": label,
            "spot": pair["spot"],
            "future": pair["future"],
            "observations": len(df),
            "avg_basis": round(df["basis"].mean(), 4),
            "avg_basis_pct": round(df["basis_pct"].mean(), 4),
            "max_basis": round(df["basis"].max(), 4),
            "min_basis": round(df["basis"].min(), 4),
            "avg_spot_mid": round(df["spot_mid"].mean(), 2),
            "avg_future_mid": round(df["future_mid"].mean(), 2),
        })

    if summary_rows:
        summary = pd.DataFrame(summary_rows)
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        summary_path = REPORTS_DIR / "summary_all_pairs.csv"
        summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"\nOzet rapor: {summary_path}")

    query_demo(conn)
    conn.close()
    print("\n[OK] Analiz tamamlandi.")


if __name__ == "__main__":
    main()
