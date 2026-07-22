import psycopg2
import pandas as pd
import matplotlib.pyplot as plt

# 1. Analiz Edilecek 10 Sembol Çifti
PAIRS = [
    ('THYAO.E', 'F_THYAO0426'),
    ('AKBNK.E', 'F_AKBNK0426'),
    ('GARAN.E', 'F_GARAN0426'),
    ('ASELS.E', 'F_ASELS0426'),
    ('TUPRS.E', 'F_TUPRS0426'),
    ('KCHOL.E', 'F_KCHOL0426'),
    ('ISCTR.E', 'F_ISCTR0426'),
    ('PGSUS.E', 'F_PGSUS0426'),
    ('BIMAS.E', 'F_BIMAS0426'),
    ('EREGL.E', 'F_EREGL0426')
]

# 2. PostgreSQL Bağlantısı
conn = psycopg2.connect("dbname=bist_lob_db user=postgres password=erenberke host=localhost port=5432")

print("=== 10 Sembol Çifti Analizi ve CSV Dışa Aktarımı Başladı ===")

for spot, futures in PAIRS:
    query = f"""
    SELECT 
        s.sequence_number,
        s.mid_price AS spot_mid,
        s.spread AS spot_spread,
        f.mid_price AS futures_mid,
        f.spread AS futures_spread
    FROM price_table_snapshots s
    JOIN price_table_snapshots f 
      ON s.sequence_number = f.sequence_number
    WHERE s.symbol = '{spot}' 
      AND f.symbol = '{futures}'
    ORDER BY s.sequence_number ASC;
    """
    
    df = pd.read_sql(query, conn)
    
    if not df.empty:
        # Basis (Fiyat Farkı) ve Momentum Hesaplamaları
        df['basis'] = df['futures_mid'] - df['spot_mid']
        df['spot_momentum'] = df['spot_mid'].diff(10)
        df['futures_momentum'] = df['futures_mid'].diff(10)
        
        # Her sembol çifti için ayrı CSV kaydetme
        clean_name = spot.split('.')[0]
        csv_filename = f"report_{clean_name}_spot_vs_futures.csv"
        df.to_csv(csv_filename, index=False)
        print(f"[OK] {csv_filename} başarıyla oluşturuldu. (Toplam Satır: {len(df)})")

conn.close()
print("\n[TÜMÜ TAMAMLANDI] 10 adet CSV raporu proje klasörüne kaydedildi!")