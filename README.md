
# 📈 BIST LOB Analysis (Limit Order Book Analytics Engine)

![C++](https://img.shields.io/badge/C++-17-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red)
![License](https://img.shields.io/badge/License-MIT-green.svg)

**BIST LOB Analysis**, Borsa İstanbul (BIST) ham emir defteri (Limit Order Book) ve ITCH protokolü verilerini yüksek performansla işleyen, PostgreSQL üzerinde zaman serisi verisi olarak depolayan ve Python/Streamlit ile nicel (quantitative) alfa sinyalleri üreten uçtan uca bir finansal veri analiz motorudur.

---

## 🏗️ Sistem Mimarisi (System Architecture)

[ BIST ITCH Data Stream ]
│
▼
┌───────────────────────────┐
│  C++17 Parsing Engine     │ ──► High-Speed Binary Parsing & LOB Rebuilding
└─────────────┬─────────────┘
│
▼
┌───────────────────────────┐
│  PostgreSQL Database      │ ──► Time-Series Tick & Order Book Snapshot Storage
└─────────────┬─────────────┘
│
▼
┌───────────────────────────┐
│  Python / Streamlit Dash  │ ──► Quantitative Metrics (OBI), Visualization & Alpha Signals
└────────────────────────────┘


---

## ⚡ Öne Çıkan Özellikler

* **Düşük Gecikmeli C++17 Motoru:** BIST ITCH protokol mesajlarını binary seviyede çözer ve milisaniye altı hassasiyetle derinlik tablosunu (LOB) yeniden inşa eder.
* **Verimli Veritabanı Mimarisi:** İşlenmiş emir defteri verilerini PostgreSQL üzerinde optimum indeksleme ve bölümlendirme ile saklar.
* **Derinlik ve Ağırlıklı OBI Analizi:** 10 kademeli ağırlıklı Order Book Imbalance (OBI) hesabı ile anlık likidite baskısını ve fiyat yönünü tahmin eder.
* **İnteraktif Dashboard:** Streamlit mimarisi ile veri akışını, derinlik grafiklerini ve alfa metriklerini görselleştirir.

---

## 📐 Matematiksel Modeller ve Metrikler

### Order Book Imbalance (OBI)
Emir defterindeki alış ve satış tarafı hacim uyumsuzluğunu ölçmek için kullanılan temel metrik:

$$OBI_t = \frac{\sum_{i=1}^{k} w_i \cdot V_{b,i} - \sum_{i=1}^{k} w_i \cdot V_{a,i}}{\sum_{i=1}^{k} w_i \cdot V_{b,i} + \sum_{i=1}^{k} w_i \cdot V_{a,i}}$$

Burada:
* $V_{b,i}$ ve $V_{a,i}$: $i$. kademedeki alış (bid) ve satış (ask) hacimleridir.
* $w_i$: Kademe uzaklığına göre belirlenen ağırlık katsayısıdır ($w_i = \frac{1}{i}$).
* $k$: İncelenen kademe sayısıdır ($k = 10$).

---

## 🛠️ Teknoloji Yığını

* **Engine:** C++17 (Boost, CMake)
* **Database:** PostgreSQL 15+
* **Analytics & UI:** Python 3.10+, Streamlit, Pandas, Matplotlib / Seaborn
* **Version Control:** Git & GitHub

---

## 📂 Proje Dizin Yapısı

```text
bist-lob-analysis/
├── cpp_engine/          # C++ ITCH parser ve LOB oluşturucu kodlar
├── db/                  # PostgreSQL şemaları ve migration scriptleri
├── app/                 # Python Streamlit arayüzü ve analiz modülleri
├── tests/               # Birim ve entegrasyon testleri
├── .gitignore           # Büyük veri dosyalarını (db_data vb.) hariç tutan kural seti
├── requirements.txt     # Python bağımlılıkları
└── README.md            # Proje dokümantasyonu
🚀 Kurulum ve Çalıştırma
1. Gereksinimler
C++17 destekli derleyici (GCC / Clang / MSVC)

CMake 3.18+

PostgreSQL 15+

Python 3.10+

2. Python Bağımlılıklarının Kurulumu
Bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
3. Arayüzün Çalıştırılması
Bash
streamlit run app/main.py