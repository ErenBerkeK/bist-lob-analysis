"""Sunum odaklı BIST L2 LOB ve spot/vadeli analiz paneli."""
import json
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import psycopg2
import streamlit as st

ROOT = Path(__file__).resolve().parent
CONN = os.environ.get("BIST_DB_CONN", "dbname=bist_lob_db")

st.set_page_config(page_title="BIST L2 LOB Analizi", page_icon="📈", layout="wide")


@st.cache_data(ttl=15)
def read_sql(query: str, params: tuple = ()) -> pd.DataFrame:
    with psycopg2.connect(CONN) as conn:
        return pd.read_sql_query(query, conn, params=params)


@st.cache_data
def load_pairs() -> list[dict]:
    with (ROOT / "config" / "symbol_pairs.json").open(encoding="utf-8") as file:
        return json.load(file)["pairs"]


def scope(alias: str, run_id: int | None) -> tuple[str, tuple]:
    return (f"{alias}.run_id IS NULL", ()) if run_id is None else (f"{alias}.run_id = %s", (run_id,))


def format_run(run_id: int | None) -> str:
    return "Eski veriler (run_id yok)" if run_id is None else f"Çalışma #{run_id}"


def load_runs() -> pd.DataFrame:
    return read_sql("""
        SELECT id, pcap_path, snapshot_every, status, started_at, finished_at
        FROM analysis_runs ORDER BY id DESC
    """)


def load_symbols(run_id: int | None) -> pd.DataFrame:
    condition, params = scope("s", run_id)
    return read_sql(f"""
        SELECT s.symbol, MIN(s.order_book_id) AS order_book_id, COUNT(*) AS snapshots
        FROM price_table_snapshots s
        WHERE {condition}
        GROUP BY s.symbol ORDER BY s.symbol
    """, params)


def sequence_bounds(run_id: int | None, symbol: str) -> tuple[int, int] | None:
    condition, run_params = scope("s", run_id)
    frame = read_sql(f"""
        SELECT MIN(sequence_number) AS min_seq, MAX(sequence_number) AS max_seq
        FROM price_table_snapshots s
        WHERE {condition} AND s.symbol = %s
    """, (*run_params, symbol))
    if frame.empty or pd.isna(frame.loc[0, "min_seq"]):
        return None
    return int(frame.loc[0, "min_seq"]), int(frame.loc[0, "max_seq"])


def pair_data(run_id: int | None, spot: str, future: str, low: int, high: int) -> pd.DataFrame:
    condition_s, params_s = scope("s", run_id)
    condition_f, params_f = scope("f", run_id)
    query = f"""
        SELECT s.sequence_number, s.event_ts_sec, s.event_ts_nsec,
               s.mid_price AS spot_mid, s.spread AS spot_spread,
               f.mid_price AS future_mid, f.spread AS future_spread
        FROM price_table_snapshots s
        JOIN price_table_snapshots f
          ON f.sequence_number = s.sequence_number
         AND {condition_f}
         AND f.symbol = %s
        WHERE {condition_s}
          AND s.symbol = %s
          AND s.sequence_number BETWEEN %s AND %s
        ORDER BY s.sequence_number
    """
    frame = read_sql(query, (*params_f, future, *params_s, spot, low, high))
    if not frame.empty:
        frame["basis"] = frame["future_mid"] - frame["spot_mid"]
        frame["spot_momentum_pct"] = frame["spot_mid"].pct_change(10).mul(100)
        frame["future_momentum_pct"] = frame["future_mid"].pct_change(10).mul(100)
    return frame


def lob_levels(run_id: int | None, symbol: str, requested_seq: int) -> tuple[pd.DataFrame, int | None]:
    condition, params = scope("s", run_id)
    query = f"""
        SELECT sequence_number,
               {', '.join(f'bid_price_{i}, bid_qty_{i}' for i in range(1, 11))},
               {', '.join(f'ask_price_{i}, ask_qty_{i}' for i in range(1, 11))}
        FROM price_table_snapshots s
        WHERE {condition} AND s.symbol = %s AND s.sequence_number <= %s
        ORDER BY s.sequence_number DESC LIMIT 1
    """
    row = read_sql(query, (*params, symbol, requested_seq))
    if row.empty:
        return pd.DataFrame(), None
    snapshot = row.iloc[0]
    levels = []
    for level in range(1, 11):
        levels.append({"Kademe": level, "Alış fiyat": snapshot[f"bid_price_{level}"], "Alış miktar": snapshot[f"bid_qty_{level}"],
                       "Satış fiyat": snapshot[f"ask_price_{level}"], "Satış miktar": snapshot[f"ask_qty_{level}"]})
    return pd.DataFrame(levels), int(snapshot["sequence_number"])


st.title("📊 BIST L2 Emir Defteri ve Spot–Vadeli Analizi")
st.caption("C++ LOB motoru · PostgreSQL snapshot deposu · Python analiz hattı")

try:
    runs = load_runs()
    legacy_exists = not load_symbols(None).empty
except Exception as error:
    st.error("Veritabanına bağlanılamadı veya şema uygulanmadı.")
    st.code("python scripts/setup_db.py")
    st.exception(error)
    st.stop()

run_options: dict[str, int | None] = {}
for _, run in runs.iterrows():
    label = f"Çalışma #{int(run.id)} · {run.status} · {run.started_at:%Y-%m-%d %H:%M}"
    run_options[label] = int(run.id)
if legacy_exists:
    run_options["Eski veriler (run_id yok)"] = None
if not run_options:
    st.warning("Henüz snapshot yok. Önce lob_engine çalıştırın.")
    st.stop()

with st.sidebar:
    st.header("Kontroller")
    selected_run_label = st.selectbox("Veri çalışması", list(run_options))
    selected_run = run_options[selected_run_label]
    st.caption("Aynı sequence numaraları yalnızca seçili çalışma içinde karşılaştırılır.")
    if st.button("Veriyi yenile"):
        st.cache_data.clear()
        st.rerun()

symbols = load_symbols(selected_run)
available = set(symbols["symbol"])
pairs = [pair for pair in load_pairs() if pair["spot"] in available and pair["future"] in available]

summary_col, details_col, count_col = st.columns(3)
summary_col.metric("Veri seçimi", format_run(selected_run))
details_col.metric("Sembol sayısı", len(symbols))
count_col.metric("Toplam snapshot", f"{int(symbols['snapshots'].sum()):,}")

tab_pair, tab_lob, tab_query = st.tabs(["Pay–Vadeli Analizi", "10 Kademe LOB", "DB Sorgu Görünümü"])

with tab_pair:
    if not pairs:
        st.info("Seçili çalışmada tanımlı spot–vadeli çiftleri bulunamadı.")
    else:
        selected_pair = st.selectbox("Sembol çifti", pairs, format_func=lambda pair: f"{pair['label']} — {pair['spot']} / {pair['future']}")
        bounds = sequence_bounds(selected_run, selected_pair["spot"])
        if bounds is None:
            st.warning("Seçilen spot sembol için snapshot bulunamadı.")
        else:
            low, high = st.slider("Sequence aralığı", min_value=bounds[0], max_value=bounds[1], value=bounds)
            frame = pair_data(selected_run, selected_pair["spot"], selected_pair["future"], low, high)
            if frame.empty:
                st.warning("Bu aralıkta ortak sequence number bulunamadı.")
            else:
                metrics = st.columns(4)
                metrics[0].metric("Eşleşen snapshot", f"{len(frame):,}")
                metrics[1].metric("Ortalama basis", f"{frame['basis'].mean():.4f}")
                metrics[2].metric("Son spot mid", f"{frame['spot_mid'].iloc[-1]:.4f}")
                metrics[3].metric("Son vadeli mid", f"{frame['future_mid'].iloc[-1]:.4f}")
                price_chart = go.Figure()
                price_chart.add_scatter(x=frame["sequence_number"], y=frame["spot_mid"], name="Spot mid")
                price_chart.add_scatter(x=frame["sequence_number"], y=frame["future_mid"], name="Vadeli mid")
                price_chart.update_layout(title="Fiyat zaman serisi", xaxis_title="Sequence number", yaxis_title="Fiyat", height=380)
                st.plotly_chart(price_chart, use_container_width=True)
                basis_chart = go.Figure()
                basis_chart.add_scatter(x=frame["sequence_number"], y=frame["basis"], name="Basis", line={"color": "purple"})
                basis_chart.update_layout(title="Basis (Vadeli − Spot)", xaxis_title="Sequence number", yaxis_title="Fiyat farkı", height=300)
                st.plotly_chart(basis_chart, use_container_width=True)
                st.download_button("Bu görünümü CSV indir", frame.to_csv(index=False).encode("utf-8-sig"),
                                   file_name=f"{selected_pair['label']}_run_{selected_run or 'legacy'}.csv", mime="text/csv")

with tab_lob:
    selected_symbol = st.selectbox("LOB sembolü", symbols["symbol"].tolist(), key="lob_symbol")
    bounds = sequence_bounds(selected_run, selected_symbol)
    if bounds:
        requested_sequence = st.number_input("İstenen sequence number", min_value=bounds[0], max_value=bounds[1], value=bounds[1], step=1)
        levels, actual_sequence = lob_levels(selected_run, selected_symbol, int(requested_sequence))
        if actual_sequence is not None:
            st.caption(f"Gösterilen en yakın snapshot sequence: {actual_sequence}")
            st.dataframe(levels, use_container_width=True, hide_index=True)
            depth = go.Figure()
            depth.add_bar(y=levels["Kademe"], x=levels["Alış miktar"], name="Alış", orientation="h")
            depth.add_bar(y=levels["Kademe"], x=-levels["Satış miktar"], name="Satış", orientation="h")
            depth.update_layout(barmode="relative", title="10 kademe derinlik", xaxis_title="Miktar (satış negatif)", yaxis_title="Kademe")
            st.plotly_chart(depth, use_container_width=True)

with tab_query:
    st.caption("Sembol, order book ID ve sequence aralığına göre filtrelenmiş snapshotlar.")
    query_symbol = st.selectbox("Sembol", symbols["symbol"].tolist(), key="query_symbol")
    query_book_id = int(symbols.loc[symbols["symbol"] == query_symbol, "order_book_id"].iloc[0])
    bounds = sequence_bounds(selected_run, query_symbol)
    if bounds:
        seq_from, seq_to = st.slider("Sorgu sequence aralığı", bounds[0], bounds[1], bounds, key="query_range")
        condition, params = scope("s", selected_run)
        rows = read_sql(f"""
            SELECT sequence_number, event_ts_sec, event_ts_nsec, order_book_id, symbol,
                   best_bid, best_ask, mid_price, spread, captured_at
            FROM price_table_snapshots s
            WHERE {condition} AND s.symbol = %s AND s.order_book_id = %s
              AND s.sequence_number BETWEEN %s AND %s
            ORDER BY s.sequence_number LIMIT 1000
        """, (*params, query_symbol, query_book_id, seq_from, seq_to))
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("Sonuç güvenlik ve sunum performansı için 1.000 satırla sınırlandırılmıştır.")
