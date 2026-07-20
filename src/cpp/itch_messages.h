#ifndef ITCH_MESSAGES_H
#define ITCH_MESSAGES_H

#include <cstdint>

#pragma pack(push, 1)

// PCAP Dosya Başlığı (Global Header - 24 Bytes)
struct PcapGlobalHeader {
    uint32_t magicNumber;   // 0xa1b2c3d4
    uint16_t versionMajor;
    uint16_t versionMinor;
    int32_t  thiszone;
    uint32_t sigfigs;
    uint32_t snaplen;
    uint32_t network;
};

// PCAP Paket Başlığı (Packet Header - 16 Bytes)
struct PcapPacketHeader {
    uint32_t tsSec;         // Zaman (saniye)
    uint32_t tsUsec;        // Zaman (mikrosaniye)
    uint32_t inclLen;       // Paketin kayıtlı uzunluğu
    uint32_t origLen;       // Paketin orijinal uzunluğu
};

// ITCH Paket Başlığı
struct PacketHeader {
    uint16_t packetLength;
    uint8_t  packetType;
};

// 1. Yeni Emir Ekleme Mesajı ('A')
struct AddOrderMessage {
    uint8_t  messageType;   // 'A'
    uint16_t stockLocate;
    uint16_t trackingNumber;
    uint64_t timestamp;
    uint64_t orderReferenceNumber;
    char     buySellIndicator; // 'B' = Alış, 'S' = Satış
    uint32_t shares;
    char     stock[8];
    uint32_t price;
};

// 2. Emir Gerçekleşme Mesajı ('E' - Order Executed)
struct OrderExecutedMessage {
    uint8_t  messageType;   // 'E'
    uint16_t stockLocate;
    uint16_t trackingNumber;
    uint64_t timestamp;
    uint64_t orderReferenceNumber;
    uint32_t executedShares;
    uint64_t matchNumber;
};

// 3. Emir İptal Mesajı ('X' - Order Cancel)
struct OrderCancelMessage {
    uint8_t  messageType;   // 'X'
    uint16_t stockLocate;
    uint16_t trackingNumber;
    uint64_t timestamp;
    uint64_t orderReferenceNumber;
    uint32_t canceledShares;
};

// 4. Emir Silme Mesajı ('D' - Order Delete)
struct OrderDeleteMessage {
    uint8_t  messageType;   // 'D'
    uint16_t stockLocate;
    uint16_t trackingNumber;
    uint64_t timestamp;
    uint64_t orderReferenceNumber;
};

#pragma pack(pop)

#endif // ITCH_MESSAGES_H