import psycopg2
import pandas as pd
import matplotlib.pyplot as plt

# 1. PostgreSQL Bağlantısı
conn = psycopg2.connect("dbname=bist_lob_db user=postgres password=erenberke host=localhost port=5432")

# 2. Pay (THYAO.E) ve Vadeli (F_THYAO0426) Verilerini Çekip Birleştirme
query = """
SELECT 
    s.sequence_number,
    s.mid_price AS spot_mid,
    s.spread AS spot_spread,
    f.mid_price AS futures_mid,
    f.spread AS futures_spread
FROM price_table_snapshots s
JOIN price_table_snapshots f 
  ON s.sequence_number = f.sequence_number
WHERE s.symbol = 'THYAO.E' 
  AND f.symbol = 'F_THYAO0426'
ORDER BY s.sequence_number ASC;
"""

df = pd.read_sql(query, conn)
conn.close()

if not df.empty:
    # 3. Pay vs. Vadeli İlişkisi Hesaplamaları
    # Basis (Fiyat Farkı) = Vadeli Fiyat - Pay Fiyatı
    df['basis'] = df['futures_mid'] - df['spot_mid']
    
    # Momentum (Fiyat Değişim Hızı - 10 snapshotluk getiri)
    df['spot_momentum'] = df['spot_mid'].diff(10)
    df['futures_momentum'] = df['futures_mid'].diff(10)

    # 4. CSV Formatında Sonuç Raporu Dışa Aktarma (İstenen Kriter)
    csv_filename = "THYAO_Spot_vs_Futures_Analysis.csv"
    df.to_csv(csv_filename, index=False)
    print(f"\n[BAŞARILI] Analiz sonuçları CSV dosyasına aktarıldı: {csv_filename}")

    # 5. Grafik Görselleştirme (Pay vs Vadeli Fiyatı ve Basis/Spread İlişkisi)
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    ax1.plot(df['sequence_number'], df['spot_mid'], label='Spot (THYAO.E)', color='blue')
    ax1.plot(df['sequence_number'], df['futures_mid'], label='Futures (F_THYAO0426)', color='orange', linestyle='--')
    ax1.set_title('THYAO Pay vs. Vadeli Fiyat İlişkisi & Momentum Analizi')
    ax1.set_ylabel('Fiyat (TL)')
    ax1.legend()
    ax1.grid(True)

    ax2.plot(df['sequence_number'], df['basis'], label='Basis (Vadeli - Spot Farkı)', color='purple')
    ax2.axhline(0, color='black', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Sequence Number')
    ax2.set_ylabel('Fiyat Farkı (TL)')
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    plt.show()
else:
    print("Veri bulunamadı! Lütfen veritabanını kontrol edin.")