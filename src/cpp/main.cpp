#include <iostream>
#include <vector>
#include <winsock2.h> // Byte order donusumleri (ntohs) icin
#pragma comment(lib, "ws2_32.lib")

#include "pcap_reader.h"

int main() {
    std::cout << "=== BIST LOB ITCH Parser (MoldUDP64) Baslatiliyor ===" << std::endl;

    PcapReader reader;
    std::string pcapPath = "data/itch-pri-20260427.pcap";

    if (!reader.open(pcapPath)) {
        std::cerr << "Lutfen .pcap dosyasini 'data/' klasorune koydugunuzdan emin olun." << std::endl;
        return 1;
    }

    PcapPacketHeader packetHeader;
    std::vector<char> packetBuffer;

    uint64_t totalPackets = 0;
    uint64_t addOrderCount = 0;
    uint64_t executeCount = 0;
    uint64_t cancelCount = 0;
    uint64_t deleteCount = 0;

    std::cout << "Paketler ve ITCH mesajlari ayristiriliyor..." << std::endl;

    while (reader.readNextPacket(packetHeader, packetBuffer)) {
        totalPackets++;

        // Minimum Ag Katmani Boyutu: Ethernet(14) + IP(20) + UDP(8) + MoldUDP64(20) = 62 bytes
        const size_t MOLDUDP_HEADER_OFFSET = 42; 
        const size_t MOLDUDP_HEADER_LEN = 20;

        if (packetBuffer.size() < (MOLDUDP_HEADER_OFFSET + MOLDUDP_HEADER_LEN)) {
            continue; // Ağ başlıklarından kısa paketleri atla
        }

        // MoldUDP64 header sonundaki Message Count (2 Bytes - Big Endian)
        uint16_t msgCount = 0;
        unsigned char* buf = reinterpret_cast<unsigned char*>(packetBuffer.data());
        msgCount = (buf[60] << 8) | buf[61];

        size_t currOffset = MOLDUDP_HEADER_OFFSET + MOLDUDP_HEADER_LEN;

        // MoldUDP paketi içindeki tüm ITCH mesajlarını sırayla tara
        for (uint16_t i = 0; i < msgCount; ++i) {
            if (currOffset + 2 > packetBuffer.size()) break;

            // Her ITCH mesajının ilk 2 byte'ı mesaj uzunluğudur
            uint16_t msgLen = (buf[currOffset] << 8) | buf[currOffset + 1];
            size_t msgDataOffset = currOffset + 2;

            if (msgDataOffset >= packetBuffer.size()) break;

            // ITCH Mesaj Tipi
            char messageType = packetBuffer[msgDataOffset];

            switch (messageType) {
                case 'A': addOrderCount++; break;
                case 'E': executeCount++; break;
                case 'X': cancelCount++; break;
                case 'D': deleteCount++; break;
                default: break;
            }

            currOffset += 2 + msgLen;
        }
    }

    std::cout << "\n=== PAKET VE MESAJ ISTATISTIKLERI ===" << std::endl;
    std::cout << "Toplam Okunan Paket: " << totalPackets << std::endl;
    std::cout << "Add Order ('A'):      " << addOrderCount << std::endl;
    std::cout << "Order Executed ('E'): " << executeCount << std::endl;
    std::cout << "Order Cancel ('X'):   " << cancelCount << std::endl;
    std::cout << "Order Delete ('D'):   " << deleteCount << std::endl;

    return 0;
}