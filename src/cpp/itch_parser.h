#ifndef ITCH_PARSER_H
#define ITCH_PARSER_H

#include <cstdint>
#include <string>
#include <cmath>

inline uint16_t parseU16(const unsigned char* p) {
    return (static_cast<uint16_t>(p[0]) << 8) | static_cast<uint16_t>(p[1]);
}

inline uint32_t parseU32(const unsigned char* p) {
    return (static_cast<uint32_t>(p[0]) << 24) | (static_cast<uint32_t>(p[1]) << 16) |
           (static_cast<uint32_t>(p[2]) << 8)  | static_cast<uint32_t>(p[3]);
}

inline int32_t parseI32(const unsigned char* p) {
    return static_cast<int32_t>(parseU32(p));
}

inline uint64_t parseU64(const unsigned char* p) {
    uint64_t val = 0;
    for (int i = 0; i < 8; ++i) {
        val = (val << 8) | static_cast<uint64_t>(p[i]);
    }
    return val;
}

inline std::string cleanAlpha(const unsigned char* p, size_t maxLen) {
    std::string s;
    s.reserve(maxLen);
    for (size_t i = 0; i < maxLen; ++i) {
        char c = static_cast<char>(p[i]);
        if (c == '\0') break;
        if (c != ' ') s += c;
    }
    return s;
}

inline double priceToDouble(int32_t rawPrice, uint16_t decimals) {
    if (rawPrice == static_cast<int32_t>(0x80000000)) {
        return 0.0;
    }
    if (decimals >= 256) {
        return static_cast<double>(rawPrice) / 256.0;
    }
    return static_cast<double>(rawPrice) / std::pow(10.0, static_cast<double>(decimals));
}

struct MoldUdpPacket {
    static constexpr size_t ETH_IP_UDP_OFFSET = 42;
    static constexpr size_t HEADER_LEN = 20;
};

#endif
