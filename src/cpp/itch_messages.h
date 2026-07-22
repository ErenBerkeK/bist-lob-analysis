#ifndef ITCH_MESSAGES_H
#define ITCH_MESSAGES_H

#include <cstdint>

#pragma pack(push, 1)

// BIST ITCH v2112 - Add Order (No MPID) 'A' - 45 bytes minimum
struct AddOrderMessage {
    char messageType;              // 0
    uint32_t timestampNanoseconds; // 1-4
    uint64_t orderId;              // 5-12
    uint32_t orderBookId;          // 13-16
    char side;                     // 17
    uint32_t rankingSequence;      // 18-21
    uint64_t quantity;             // 22-29
    int32_t price;                 // 30-33 (signed)
    uint16_t orderAttributes;      // 34-35
    uint8_t lotType;               // 36
    uint64_t rankingTime;          // 37-44
};

// Order Book Directory 'R'
struct OrderBookDirectoryMessage {
    char messageType;              // 0
    uint32_t timestampNanoseconds; // 1-4
    uint32_t orderBookId;          // 5-8
    char symbol[32];               // 9-40
};

// Order Executed 'E'
struct OrderExecutedMessage {
    char messageType;              // 0
    uint32_t timestampNanoseconds; // 1-4
    uint64_t orderId;              // 5-12
    uint32_t orderBookId;          // 13-16
    char side;                     // 17
    uint64_t executedQuantity;       // 18-25
};

// Order Delete 'D'
struct OrderDeleteMessage {
    char messageType;              // 0
    uint32_t timestampNanoseconds; // 1-4
    uint64_t orderId;              // 5-12
    uint32_t orderBookId;          // 13-16
    char side;                     // 17
};

#pragma pack(pop)

#endif
