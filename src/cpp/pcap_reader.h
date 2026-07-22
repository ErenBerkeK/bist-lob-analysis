#ifndef PCAP_READER_H
#define PCAP_READER_H

#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstdint>

#pragma pack(push, 1)

// PCAP Genel Dosya Başlığı (24 Bytes)
struct PcapGlobalHeader {
    uint32_t magic_number;   // Magic Number (0xa1b2c3d4)
    uint16_t version_major;  // Major Versiyon
    uint16_t version_minor;  // Minor Versiyon
    int32_t  thiszone;       // GMT Zaman Düzeltmesi
    uint32_t sigfigs;        // Zaman Damgası Hassasiyeti
    uint32_t snaplen;        // Maksimum Paket Boyutu
    uint32_t network;        // Data Link Tipi
};

// PCAP Paket Başlığı (16 Bytes)
struct PcapPacketHeader {
    uint32_t ts_sec;         // Zaman Damgası (Saniye)
    uint32_t ts_usec;        // Zaman Damgası (Mikrosaniye)
    uint32_t inclLen;        // Dosyadaki Paket Boyutu
    uint32_t origLen;        // Gerçek Paket Boyutu
};

#pragma pack(pop)

class PcapReader {
private:
    std::ifstream file;
    PcapGlobalHeader globalHeader;

public:
    PcapReader() {}

    ~PcapReader() {
        if (file.is_open()) {
            file.close();
        }
    }

    bool open(const std::string& filePath) {
        file.open(filePath, std::ios::binary);
        if (!file.is_open()) {
            std::cerr << "Hata: PCAP dosyasi acilamadi -> " << filePath << std::endl;
            return false;
        }

        file.read(reinterpret_cast<char*>(&globalHeader), sizeof(PcapGlobalHeader));
        if (file.gcount() != sizeof(PcapGlobalHeader)) {
            std::cerr << "Hata: PCAP basligi okunamadi!" << std::endl;
            return false;
        }

        std::cout << "[SUCCESS] PCAP dosyasi basariyla acildi!" << std::endl;
        return true;
    }

    bool readNextPacket(PcapPacketHeader& packetHeader, std::vector<char>& packetBuffer) {
        if (!file.is_open() || file.eof()) return false;

        file.read(reinterpret_cast<char*>(&packetHeader), sizeof(PcapPacketHeader));
        if (file.gcount() < sizeof(PcapPacketHeader)) return false;

        packetBuffer.resize(packetHeader.inclLen);
        file.read(packetBuffer.data(), packetHeader.inclLen);
        return file.gcount() == packetHeader.inclLen;
    }
};

#endif // PCAP_READER_H