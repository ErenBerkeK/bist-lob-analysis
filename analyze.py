import psycopg2
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 1. PostgreSQL Bağlantısı
conn = psycopg2.connect("dbname=bist_lob_db user=postgres password=erenberke host=localhost port=5432")

# 2. 10 Kademeli Derinlik Verilerini Çek
query = """
SELECT sequence_number, mid_price,
       bid_qty_1, bid_qty_2, bid_qty_3, bid_qty_4, bid_qty_5, bid_qty_6, bid_qty_7, bid_qty_8, bid_qty_9, bid_qty_10,
       ask_qty_1, ask_qty_2, ask_qty_3, ask_qty_4, ask_qty_5, ask_qty_6, ask_qty_7, ask_qty_8, ask_qty_9, ask_qty_10
FROM price_table_snapshots
WHERE symbol = 'THYAO.E'
ORDER BY sequence_number ASC;
"""
df = pd.read_sql(query, conn)
conn.close()

if not df.empty:
    # 3. Kademelere Azalan Ağırlık Kat sayısı (Üstel Azalma - Exponential Decay)
    # 1. Kademe en yüksek ağırlığa (1.0), 10. Kademe en düşük ağırlığa sahip olur
    weights = np.exp(-0.4 * np.arange(10)) 
    
    bid_cols = [f'bid_qty_{i}' for i in range(1, 11)]
    ask_cols = [f'ask_qty_{i}' for i in range(1, 11)]
    
    weighted_bid = (df[bid_cols].values * weights).sum(axis=1)
    weighted_ask = (df[ask_cols].values * weights).sum(axis=1)
    
    # 10 Kademeli Ağırlıklı OBI
    df['weighted_obi'] = (weighted_bid - weighted_ask) / (weighted_bid + weighted_ask + 1e-8)
    
    # Sinyal Yumuşatma (50 Snapshotluk Hareketli Ortalama)
    df['obi_smoothed'] = df['weighted_obi'].rolling(window=50).mean()
    
    # Gelecekteki Fiyat Değişimi (50 snapshot sonraki return)
    df['future_return'] = df['mid_price'].shift(-50) - df['mid_price']
    
    # OBI Sinyali ile Gelecekteki Fiyat Arasındaki Korelasyon
    corr = df['obi_smoothed'].corr(df['future_return'])
    print(f"\n==================================================")
    print(f"10-Kademe Ağırlıklı OBI - Fiyat Değişimi Korelasyonu: {corr:.4f}")
    print(f"==================================================\n")

    # 4. Grafik Görselleştirme
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax1.plot(df['sequence_number'], df['mid_price'], color='blue', label='Mid Price')
    ax1.set_title(f'THYAO.E Multi-Level Weighted OBI (Alpha Sinyal Korelasyonu: {corr:.4f})')
    ax1.set_ylabel('Fiyat (TL)')
    ax1.legend()
    ax1.grid(True)

    ax2.plot(df['sequence_number'], df['obi_smoothed'], color='darkgreen', label='50-Period Smoothed 10-Level OBI')
    ax2.axhline(0, color='black', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Sequence Number')
    ax2.set_ylabel('Ağırlıklı OBI (-1 ile +1)')
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    plt.show()