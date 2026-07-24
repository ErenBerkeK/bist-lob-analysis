# High-Frequency BIST L2 Limit Order Book (LOB) Engine & Quant Pipeline

A high-performance C++17 market data parser and LOB reconstruction engine for Borsa İstanbul (BIST), integrated with PostgreSQL persistence and Python quantitative analysis tools.

## 🚀 Key Features

- **C++17 High Performance Engine:** Parses binary NASDAQ ITCH protocol packets encapsulated in Ethernet/IP/UDP/MoldUDP64 frames.
- **Real-Time Level-2 Reconstruction:** Maintains order book depth up to 10 levels for equities (`.E`) and futures contracts (`F_`).
- **Zero-Copy Memory Design:** Utilizes `std::unordered_map` and flat price-level buffers for sub-microsecond snapshot generation.
- **PostgreSQL Persistence:** Auto-schema migration, prepared batch statements, and composite B-Tree indexes on `(symbol, sequence_number)`.
- **Quantitative Alpha Research:** Calculates 10-level Exponentially-Weighted Order Book Imbalance (OBI) and short-term future return correlations.

## 🏗 System Architecture
[ PCAP Market Data ] ──> [ C++ MoldUDP64 / ITCH Parser ]
│
▼
[ L2 Order Book Engine (10 Levels) ]
│
▼
[ PostgreSQL Database (Index Optimized) ]
│
▼
[ Python Quant Analytics & OBI Signals ]
## 📊 Quant Alpha Metrics

Order Book Imbalance ($OBI$) across 10 price levels using exponential weight decay ($w_i = e^{-0.4(i-1)}$):

$$OBI = \frac{\sum_{i=1}^{10} w_i \cdot Q_{bid,i} - \sum_{i=1}^{10} w_i \cdot Q_{ask,i}}{\sum_{i=1}^{10} w_i \cdot Q_{bid,i} + \sum_{i=1}^{10} w_i \cdot Q_{ask,i}}$$

## 💻 Tech Stack
- **Language:** C++17, Python 3.10+
- **Database:** PostgreSQL 15+ (`libpq`)
- **Libraries:** Pandas, NumPy, Matplotlib, `psycopg2`
- **Protocol Standards:** BIST ITCH v1.0, MoldUDP64

## Çalıştırma ayarları

PCAP dosya yolu ve veritabanı parolası kaynak koda yazılmaz. PowerShell
oturumunda aşağıdaki değişkenleri ayarlayın (örnek değerler için
`.env.example` dosyasına bakın):

```powershell
$env:BIST_PCAP_PATH = 'C:/veri/itch-pri-20260427.pcap'
$env:BIST_DB_CONN = 'dbname=bist_lob_db host=localhost port=5432 user=postgres'
$env:PGPASSWORD = 'parolaniz'
```

Ardından CMake ile derleyip motoru çalıştırın:

```powershell
cmake -S . -B build
cmake --build build --config Release
.\build\Release\lob_engine.exe --snapshot-every 5000
```

PostgreSQL standart konumda bulunamazsa yapılandırma sırasında konumunu
belirtin:

```powershell
cmake -S . -B build -DPostgreSQL_ROOT='C:/Program Files/PostgreSQL/18'
```
