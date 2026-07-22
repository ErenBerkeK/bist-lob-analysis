#define NOMINMAX
#define WIN32_LEAN_AND_MEAN

#include <iostream>
#include <vector>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <map>
#include <iomanip>
#include <sstream>
#include <algorithm>
#include <winsock2.h>
#pragma comment(lib, "ws2_32.lib")

#include "pcap_reader.h"
#include "itch_parser.h"
#include "order_book.h"
#include <libpq-fe.h>

struct BookMeta {
    std::string symbol;
    uint16_t priceDecimals = 2;
    int16_t financialProduct = 0;
};

struct ActiveOrder {
    std::string symbol;
    char side = 'B';
    double price = 0.0;
    uint64_t shares = 0;
    uint32_t obId = 0;
};

struct LevelRow {
    double price;
    uint64_t qty;
};

static const std::unordered_set<std::string> TARGET_SYMBOLS = {
    "AKBNK.E", "F_AKBNK0426",
    "ASELS.E", "F_ASELS0426",
    "BIMAS.E", "F_BIMAS0426",
    "EREGL.E", "F_EREGL0426",
    "GARAN.E", "F_GARAN0426",
    "ISCTR.E", "F_ISCTR0426",
    "KCHOL.E", "F_KCHOL0426",
    "PGSUS.E", "F_PGSUS0426",
    "THYAO.E", "F_THYAO0426",
    "TUPRS.E", "F_TUPRS0426"
};

static bool isTargetSymbol(const std::string& sym) {
    return TARGET_SYMBOLS.count(sym) > 0;
}

static double toPrice(int32_t raw, uint16_t decimals) {
    double div = 1.0;
    for (uint16_t i = 0; i < decimals; ++i) div *= 10.0;
    return static_cast<double>(raw) / div;
}

static std::string sqlEscape(const std::string& s) {
    std::string out;
    out.reserve(s.size());
    for (char c : s) {
        if (c == '\'') out += "''";
        else out += c;
    }
    return out;
}

static bool execSql(PGconn* conn, const std::string& sql) {
    PGresult* res = PQexec(conn, sql.c_str());
    ExecStatusType st = PQresultStatus(res);
    if (st != PGRES_COMMAND_OK && st != PGRES_TUPLES_OK) {
        std::cerr << "[SQL HATA] " << PQerrorMessage(conn) << std::endl;
        PQclear(res);
        return false;
    }
    PQclear(res);
    return true;
}

static void adjustLevel(OrderBookLevel& book, char side, double price, int64_t delta) {
    if (price <= 0.0 || delta == 0) return;
    if (side == 'B') {
        int64_t next = static_cast<int64_t>(book.bids[price]) + delta;
        if (next <= 0) book.bids.erase(price);
        else book.bids[price] = static_cast<uint64_t>(next);
    } else if (side == 'S') {
        int64_t next = static_cast<int64_t>(book.asks[price]) + delta;
        if (next <= 0) book.asks.erase(price);
        else book.asks[price] = static_cast<uint64_t>(next);
    }
}

static std::vector<LevelRow> topBids(const OrderBookLevel& book, int n) {
    std::vector<LevelRow> out;
    for (const auto& pair : book.bids) {
        if (pair.second == 0) continue;
        out.push_back(LevelRow{pair.first, pair.second});
        if (static_cast<int>(out.size()) >= n) break;
    }
    return out;
}

static std::vector<LevelRow> topAsks(const OrderBookLevel& book, int n) {
    std::vector<LevelRow> out;
    for (const auto& pair : book.asks) {
        if (pair.second == 0) continue;
        out.push_back(LevelRow{pair.first, pair.second});
        if (static_cast<int>(out.size()) >= n) break;
    }
    return out;
}

static std::string buildSnapshotInsert(
    uint64_t seq, uint32_t obId, const std::string& sym,
    uint32_t tsSec, uint32_t tsNsec,
    const OrderBookLevel& book)
{
    auto bids = topBids(book, 10);
    auto asks = topAsks(book, 10);

    double bestBid = bids.empty() ? 0.0 : bids[0].price;
    double bestAsk = asks.empty() ? 0.0 : asks[0].price;
    double mid = (bestBid > 0.0 && bestAsk > 0.0) ? (bestBid + bestAsk) / 2.0 : 0.0;
    double spread = (bestBid > 0.0 && bestAsk > 0.0) ? (bestAsk - bestBid) : 0.0;

    std::ostringstream q;
    q << std::fixed << std::setprecision(4);
    q << "INSERT INTO price_table_snapshots (sequence_number,event_ts_sec,event_ts_nsec,order_book_id,symbol,"
         "best_bid,best_ask,mid_price,spread";

    for (int i = 1; i <= 10; ++i) q << ",bid_price_" << i << ",bid_qty_" << i;
    for (int i = 1; i <= 10; ++i) q << ",ask_price_" << i << ",ask_qty_" << i;
    q << ") VALUES (" << seq << "," << tsSec << "," << tsNsec << "," << obId << ",'"
      << sqlEscape(sym) << "'," << bestBid << "," << bestAsk << "," << mid << "," << spread;

    for (size_t i = 0; i < 10; ++i) {
        q << "," << (i < bids.size() ? bids[i].price : 0.0);
        q << "," << (i < bids.size() ? bids[i].qty : 0);
    }
    for (size_t i = 0; i < 10; ++i) {
        q << "," << (i < asks.size() ? asks[i].price : 0.0);
        q << "," << (i < asks.size() ? asks[i].qty : 0);
    }
    q << ");";
    return q.str();
}

int main(int argc, char* argv[]) {
    try {
        std::string pcapPath = "C:/Users/HUAWEI/Desktop/bist-lob-analysis/data/itch-pri-20260427.pcap";
        std::string connStr = "dbname=bist_lob_db user=postgres password=erenberke host=localhost port=5432";
        uint64_t maxPackets = 0;
        uint64_t snapshotEvery = 5000;

        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--pcap" && i + 1 < argc) pcapPath = argv[++i];
            else if (arg == "--max-packets" && i + 1 < argc) maxPackets = std::stoull(argv[++i]);
            else if (arg == "--snapshot-every" && i + 1 < argc) snapshotEvery = std::stoull(argv[++i]);
            else if (arg == "--conn" && i + 1 < argc) connStr = argv[++i];
        }

        std::cout << "=== BIST L2 Order Book ve Snapshot Motoru ===" << std::endl;

        PGconn* dbConn = PQconnectdb(connStr.c_str());
        if (PQstatus(dbConn) != CONNECTION_OK) {
            std::cerr << "[HATA] PostgreSQL baglantisi kurulamadi: " << PQerrorMessage(dbConn) << std::endl;
            PQfinish(dbConn);
            return 1;
        }
        std::cout << "[OK] PostgreSQL baglantisi kuruldu." << std::endl;

        execSql(dbConn, "CREATE TABLE IF NOT EXISTS order_book_directory ("
            "order_book_id INTEGER PRIMARY KEY, symbol VARCHAR(32) NOT NULL,"
            "financial_product SMALLINT, price_decimals SMALLINT NOT NULL DEFAULT 2,"
            "isin VARCHAR(12), created_at TIMESTAMPTZ DEFAULT NOW());");

        execSql(dbConn, "CREATE TABLE IF NOT EXISTS price_table_snapshots ("
            "id BIGSERIAL PRIMARY KEY, sequence_number BIGINT NOT NULL,"
            "event_ts_sec BIGINT, event_ts_nsec BIGINT, order_book_id INTEGER NOT NULL,"
            "symbol VARCHAR(32) NOT NULL, best_bid DOUBLE PRECISION, best_ask DOUBLE PRECISION,"
            "mid_price DOUBLE PRECISION, spread DOUBLE PRECISION,"
            "bid_price_1 DOUBLE PRECISION, bid_qty_1 BIGINT, bid_price_2 DOUBLE PRECISION, bid_qty_2 BIGINT,"
            "bid_price_3 DOUBLE PRECISION, bid_qty_3 BIGINT, bid_price_4 DOUBLE PRECISION, bid_qty_4 BIGINT,"
            "bid_price_5 DOUBLE PRECISION, bid_qty_5 BIGINT, bid_price_6 DOUBLE PRECISION, bid_qty_6 BIGINT,"
            "bid_price_7 DOUBLE PRECISION, bid_qty_7 BIGINT, bid_price_8 DOUBLE PRECISION, bid_qty_8 BIGINT,"
            "bid_price_9 DOUBLE PRECISION, bid_qty_9 BIGINT, bid_price_10 DOUBLE PRECISION, bid_qty_10 BIGINT,"
            "ask_price_1 DOUBLE PRECISION, ask_qty_1 BIGINT, ask_price_2 DOUBLE PRECISION, ask_qty_2 BIGINT,"
            "ask_price_3 DOUBLE PRECISION, ask_qty_3 BIGINT, ask_price_4 DOUBLE PRECISION, ask_qty_4 BIGINT,"
            "ask_price_5 DOUBLE PRECISION, ask_qty_5 BIGINT, ask_price_6 DOUBLE PRECISION, ask_qty_6 BIGINT,"
            "ask_price_7 DOUBLE PRECISION, ask_qty_7 BIGINT, ask_price_8 DOUBLE PRECISION, ask_qty_8 BIGINT,"
            "ask_price_9 DOUBLE PRECISION, ask_qty_9 BIGINT, ask_price_10 DOUBLE PRECISION, ask_qty_10 BIGINT,"
            "captured_at TIMESTAMPTZ DEFAULT NOW());");

        std::unordered_map<uint32_t, BookMeta> bookMeta;
        std::unordered_map<std::string, OrderBookLevel> l2Books;
        std::unordered_map<uint64_t, ActiveOrder> activeOrders;

        PcapReader reader;
        if (!reader.open(pcapPath)) {
            PQfinish(dbConn);
            return 1;
        }

        PcapPacketHeader packetHeader;
        std::vector<char> packetBuffer;
        uint64_t processedPackets = 0;
        uint64_t sequenceCounter = 0;
        uint64_t eventsSinceSnapshot = 0;
        std::vector<std::string> pendingSql;
        pendingSql.reserve(1000);

        execSql(dbConn, "BEGIN;");

        while (reader.readNextPacket(packetHeader, packetBuffer)) {
            ++processedPackets;
            if (maxPackets > 0 && processedPackets > maxPackets) break;

            if (packetBuffer.size() < MoldUdpPacket::ETH_IP_UDP_OFFSET + MoldUdpPacket::HEADER_LEN) continue;

            const unsigned char* buf = reinterpret_cast<const unsigned char*>(packetBuffer.data());
            const unsigned char* payload = buf + MoldUdpPacket::ETH_IP_UDP_OFFSET;
            size_t payloadLen = packetBuffer.size() - MoldUdpPacket::ETH_IP_UDP_OFFSET;

            if (payloadLen < MoldUdpPacket::HEADER_LEN) continue;
            uint16_t msgCount = parseU16(payload + 18);
            if (msgCount == 0 || msgCount > 500) continue;

            size_t currOffset = MoldUdpPacket::HEADER_LEN;
            for (uint16_t i = 0; i < msgCount; ++i) {
                if (currOffset + 2 > payloadLen) break;
                uint16_t msgLen = parseU16(payload + currOffset);
                size_t msgDataOffset = currOffset + 2;
                if (msgDataOffset + msgLen > payloadLen) break;

                const unsigned char* msg = payload + msgDataOffset;
                char msgType = static_cast<char>(msg[0]);
                uint32_t tsNsec = (msgLen >= 5) ? parseU32(msg + 1) : 0;

                if (msgType == 'R' && msgLen >= 95) {
                    uint32_t obId = parseU32(msg + 5);
                    std::string sym = cleanAlpha(msg + 9, 32);
                    if (obId > 0 && !sym.empty() && isTargetSymbol(sym)) {
                        BookMeta meta;
                        meta.symbol = sym;
                        meta.financialProduct = static_cast<int16_t>(msg[85]);
                        meta.priceDecimals = parseU16(msg + 89);
                        bookMeta[obId] = meta;

                        std::ostringstream ins;
                        ins << "INSERT INTO order_book_directory (order_book_id,symbol,financial_product,price_decimals,isin) "
                            << "VALUES (" << obId << ",'" << sqlEscape(sym) << "'," << static_cast<int>(meta.financialProduct)
                            << "," << meta.priceDecimals << ",'" << sqlEscape(cleanAlpha(msg + 73, 12)) << "') "
                            << "ON CONFLICT (order_book_id) DO UPDATE SET symbol=EXCLUDED.symbol, price_decimals=EXCLUDED.price_decimals;";
                        pendingSql.push_back(ins.str());
                    }
                }
                else if ((msgType == 'A' && msgLen >= 36) || (msgType == 'F' && msgLen >= 40)) {
                    uint64_t orderId = parseU64(msg + 5);
                    uint32_t obId = parseU32(msg + 13);
                    char side = static_cast<char>(msg[17]);
                    uint64_t qty = parseU64(msg + 22);
                    int32_t rawPrice = parseI32(msg + 30);

                    auto metaIt = bookMeta.find(obId);
                    if (metaIt != bookMeta.end() && qty > 0 && (side == 'B' || side == 'S')) {
                        double price = toPrice(rawPrice, metaIt->second.priceDecimals);
                        if (price > 0.0) {
                            const std::string& symName = metaIt->second.symbol;
                            activeOrders[orderId] = ActiveOrder{symName, side, price, qty, obId};
                            adjustLevel(l2Books[symName], side, price, static_cast<int64_t>(qty));
                            ++sequenceCounter;
                            ++eventsSinceSnapshot;
                        }
                    }
                }
                else if ((msgType == 'E' || msgType == 'C') && msgLen >= 26) {
                    uint64_t orderId = parseU64(msg + 5);
                    uint64_t execQty = parseU64(msg + 17);
                    auto it = activeOrders.find(orderId);
                    if (it != activeOrders.end()) {
                        auto& ord = it->second;
                        uint64_t applied = std::min(execQty, ord.shares);
                        adjustLevel(l2Books[ord.symbol], ord.side, ord.price, -static_cast<int64_t>(applied));
                        if (ord.shares > applied) ord.shares -= applied;
                        else activeOrders.erase(it);
                        ++sequenceCounter;
                        ++eventsSinceSnapshot;
                    }
                }
                else if (msgType == 'X' && msgLen >= 25) {
                    uint64_t orderId = parseU64(msg + 5);
                    uint64_t cancelQty = parseU64(msg + 17);
                    auto it = activeOrders.find(orderId);
                    if (it != activeOrders.end()) {
                        auto& ord = it->second;
                        uint64_t applied = std::min(cancelQty, ord.shares);
                        adjustLevel(l2Books[ord.symbol], ord.side, ord.price, -static_cast<int64_t>(applied));
                        if (ord.shares > applied) ord.shares -= applied;
                        else activeOrders.erase(it);
                        ++sequenceCounter;
                        ++eventsSinceSnapshot;
                    }
                }
                else if (msgType == 'D' && msgLen >= 17) {
                    uint64_t orderId = parseU64(msg + 5);
                    auto it = activeOrders.find(orderId);
                    if (it != activeOrders.end()) {
                        auto& ord = it->second;
                        adjustLevel(l2Books[ord.symbol], ord.side, ord.price, -static_cast<int64_t>(ord.shares));
                        activeOrders.erase(it);
                        ++sequenceCounter;
                        ++eventsSinceSnapshot;
                    }
                }

                if (eventsSinceSnapshot >= snapshotEvery) {
                    for (const auto& target : TARGET_SYMBOLS) {
                        auto bookIt = l2Books.find(target);
                        if (bookIt == l2Books.end()) continue;
                        uint32_t obId = 0;
                        for (const auto& pair : bookMeta) {
                            if (pair.second.symbol == target) { obId = pair.first; break; }
                        }
                        if (obId == 0) continue;
                        pendingSql.push_back(buildSnapshotInsert(
                            sequenceCounter, obId, target, packetHeader.ts_sec, tsNsec, bookIt->second));
                    }
                    eventsSinceSnapshot = 0;
                }

                if (pendingSql.size() >= 500) {
                    for (const auto& sql : pendingSql) execSql(dbConn, sql);
                    pendingSql.clear();
                }

                currOffset += 2 + msgLen;
            }

            if (processedPackets % 1000000 == 0) {
                std::cout << "[BILGI] " << (processedPackets / 1000000) << "M paket | Aktif Emir: "
                          << activeOrders.size() << " | Seq: " << sequenceCounter << std::endl;
            }
        }

        for (const auto& sql : pendingSql) execSql(dbConn, sql);
        execSql(dbConn, "COMMIT;");
        PQfinish(dbConn);

        std::cout << "\n[ISLEM TAMAMLANDI]" << std::endl;
        std::cout << "  Toplam Paket: " << processedPackets << std::endl;
        std::cout << "  Olay Sayisi (Seq): " << sequenceCounter << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "[KRITIK HATA] " << e.what() << std::endl;
        return 1;
    }
    return 0;
}