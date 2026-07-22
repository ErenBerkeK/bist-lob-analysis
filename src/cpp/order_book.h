#ifndef ORDER_BOOK_H
#define ORDER_BOOK_H

#include <map>
#include <string>
#include <unordered_map>
#include <algorithm>
#include <cstdint>
#include "itch_messages.h"

struct OrderBookLevel {
    std::map<double, uint64_t, std::greater<double>> bids;
    std::map<double, uint64_t, std::less<double>> asks;
};

class OrderBook {
private:
    std::unordered_map<std::string, OrderBookLevel> books_;

public:
    void addOrder(uint64_t orderId, const std::string& symbol, char side, double price, uint64_t shares) {
        if (price <= 0.0 || shares == 0) return;
        auto& book = books_[symbol]; 
        if (side == 'B') {
            book.bids[price] += shares;
        } else if (side == 'S') {
            book.asks[price] += shares;
        }
    }

    void executeOrder(uint64_t orderId, uint64_t executedShares, const std::unordered_map<uint64_t, std::tuple<std::string, char, double, uint64_t>>& activeOrders) {
        // İlgili emir takibi için yardımcı metot
    }

    const OrderBookLevel* getBook(const std::string& symbol) const {
        auto it = books_.find(symbol);
        if (it != books_.end()) {
            return &it->second;
        }
        return nullptr;
    }

    const std::unordered_map<std::string, OrderBookLevel>& getAllBooks() const {
        return books_;
    }
};

#endif // ORDER_BOOK_H