"""BIST spot/vadeli çiftlerini seçili bir LOB çalışması için analiz eder."""
import argparse
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psycopg2

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "symbol_pairs.json"
DEFAULT_OUTPUT_DIR = ROOT / "output"
CONN = os.environ.get("BIST_DB_CONN", "dbname=bist_lob_db")


def load_pairs() -> list[dict]:
    with CONFIG.open(encoding="utf-8") as file:
        return json.load(file)["pairs"]


def resolve_run_id(conn, requested_run_id: int | None) -> int | None:
    """Son tamamlanan çalışmayı seçer; eski veriler için None döner."""
    if requested_run_id is not None:
        return requested_run_id
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id FROM analysis_runs
            WHERE status = 'completed'
            ORDER BY finished_at DESC NULLS LAST, id DESC
            LIMIT 1
        """)
        row = cur.fetchone()
    return row[0] if row else None


def run_filter(run_id: int | None) -> tuple[str, tuple]:
    if run_id is None:
        return "run_id IS NULL", ()
    return "run_id = %s", (run_id,)


def fetch_snapshots(conn, symbol: str, run_id: int | None) -> pd.DataFrame:
    """Sembol/sequence başına tek snapshot döndürür; eski tekrarları ayıklar."""
    where_run, run_params = run_filter(run_id)
    query = f"""
        SELECT DISTINCT ON (symbol, sequence_number)
            sequence_number, event_ts_sec, event_ts_nsec, order_book_id, symbol,
            best_bid, best_ask, mid_price, spread,
            {', '.join(f'bid_qty_{i}' for i in range(1, 11))},
            {', '.join(f'ask_qty_{i}' for i in range(1, 11))}
        FROM price_table_snapshots
        WHERE symbol = %s AND {where_run} AND mid_price > 0
        ORDER BY symbol, sequence_number, captured_at DESC, id DESC
    """
    return pd.read_sql_query(query, conn, params=(symbol, *run_params))


def weighted_obi(frame: pd.DataFrame) -> pd.Series:
    weights = np.exp(-0.4 * np.arange(10))
    bid = frame[[f"bid_qty_{i}" for i in range(1, 11)]].fillna(0).to_numpy(dtype=float)
    ask = frame[[f"ask_qty_{i}" for i in range(1, 11)]].fillna(0).to_numpy(dtype=float)
    weighted_bid = bid @ weights
    weighted_ask = ask @ weights
    denominator = weighted_bid + weighted_ask
    return pd.Series(
        np.divide(weighted_bid - weighted_ask, denominator,
                  out=np.zeros_like(denominator), where=denominator != 0),
        index=frame.index,
    )


def analyze_pair(conn, pair: dict, run_id: int | None) -> pd.DataFrame:
    spot = fetch_snapshots(conn, pair["spot"], run_id)
    future = fetch_snapshots(conn, pair["future"], run_id)
    if spot.empty or future.empty:
        print(f"[UYARI] {pair['label']}: veri yok (spot={len(spot)}, vadeli={len(future)})")
        return pd.DataFrame()

    spot["spot_obi_10"] = weighted_obi(spot)
    future["future_obi_10"] = weighted_obi(future)
    spot = spot.rename(columns={
        "sequence_number": "seq", "mid_price": "spot_mid", "best_bid": "spot_bid",
        "best_ask": "spot_ask", "spread": "spot_spread",
    })
    future = future.rename(columns={
        "sequence_number": "seq", "mid_price": "future_mid", "best_bid": "future_bid",
        "best_ask": "future_ask", "spread": "future_spread",
    })

    columns_spot = ["seq", "event_ts_sec", "event_ts_nsec", "order_book_id", "spot_mid", "spot_bid", "spot_ask", "spot_spread", "spot_obi_10"]
    columns_future = ["seq", "future_mid", "future_bid", "future_ask", "future_spread", "future_obi_10"]
    merged = pd.merge(spot[columns_spot], future[columns_future], on="seq", how="inner", validate="one_to_one")
    if merged.empty:
        print(f"[UYARI] {pair['label']}: ortak sequence bulunamadı.")
        return merged

    merged["run_id"] = run_id
    merged["pair"] = pair["label"]
    merged["spot_symbol"] = pair["spot"]
    merged["future_symbol"] = pair["future"]
    merged["basis"] = merged["future_mid"] - merged["spot_mid"]
    merged["basis_pct"] = np.where(merged["spot_mid"] != 0, merged["basis"] / merged["spot_mid"] * 100, np.nan)
    merged["spot_momentum_pct"] = merged["spot_mid"].pct_change(periods=10).mul(100)
    merged["future_momentum_pct"] = merged["future_mid"].pct_change(periods=10).mul(100)
    merged["momentum_spread_pct"] = merged["future_momentum_pct"] - merged["spot_momentum_pct"]
    return merged


def save_report(frame: pd.DataFrame, label: str, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    path = reports_dir / f"{label}_analysis.csv"
    frame.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  CSV: {path}")


def save_chart(frame: pd.DataFrame, label: str, charts_dir: Path) -> None:
    charts_dir.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(f"{label}: Pay / Vadeli Analizi")
    axes[0].plot(frame["seq"], frame["spot_mid"], label="Pay")
    axes[0].plot(frame["seq"], frame["future_mid"], label="Vadeli")
    axes[0].set_ylabel("Mid fiyat")
    axes[0].legend(); axes[0].grid(alpha=0.3)
    axes[1].plot(frame["seq"], frame["basis"], color="purple", label="Basis")
    axes[1].axhline(0, color="gray", linestyle="--", linewidth=0.8)
    axes[1].set_ylabel("Vadeli - Pay")
    axes[1].grid(alpha=0.3)
    axes[2].plot(frame["seq"], frame["spot_obi_10"], label="Pay OBI-10")
    axes[2].plot(frame["seq"], frame["future_obi_10"], label="Vadeli OBI-10")
    axes[2].set_xlabel("Sequence number")
    axes[2].set_ylabel("OBI")
    axes[2].legend(); axes[2].grid(alpha=0.3)
    fig.tight_layout()
    path = charts_dir / f"{label}_analysis.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Grafik: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="BIST spot/vadeli LOB analizi")
    parser.add_argument("--run-id", type=int, help="Analiz edilecek analysis_runs.id")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    with psycopg2.connect(CONN) as conn:
        run_id = resolve_run_id(conn, args.run_id)
        mode = f"run_id={run_id}" if run_id is not None else "eski (run_id NULL) veri"
        print(f"=== BIST Pay/Vadeli Analiz: {mode} ===")
        summaries = []
        for pair in load_pairs():
            print(f"\nAnaliz: {pair['spot']} / {pair['future']}")
            frame = analyze_pair(conn, pair, run_id)
            if frame.empty:
                continue
            save_report(frame, pair["label"], args.output_dir / "reports")
            save_chart(frame, pair["label"], args.output_dir / "charts")
            summaries.append({
                "run_id": run_id, "pair": pair["label"], "spot": pair["spot"], "future": pair["future"],
                "observations": len(frame), "avg_basis": frame["basis"].mean(),
                "avg_basis_pct": frame["basis_pct"].mean(), "max_basis": frame["basis"].max(),
                "min_basis": frame["basis"].min(), "avg_spot_obi_10": frame["spot_obi_10"].mean(),
                "avg_future_obi_10": frame["future_obi_10"].mean(),
            })

    if summaries:
        reports_dir = args.output_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(summaries).to_csv(reports_dir / "summary_all_pairs.csv", index=False, encoding="utf-8-sig")
        print(f"\n[OK] {len(summaries)} çift için rapor üretildi.")
    else:
        print("\n[UYARI] Rapor üretilemedi; seçili çalışma için çift verisini kontrol edin.")


if __name__ == "__main__":
    main()
