#ifndef PCAP_READER_H
#define PCAP_READER_H

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include "itch_messages.h"

class PcapReader {
private:
    std::ifstream file;
    PcapGlobalHeader globalHeader;

public:
    bool open(const std::string& filepath) {
        file.open(filepath, std::ios::binary);
        if (!file.is_open()) {
            std::cerr << "Hata: PCAP dosyasi acilamadi -> " << filepath << std::endl;
            return false;
        }

        // Global Header'i oku (24 Bytes)
        file.read(reinterpret_cast<char*>(&globalHeader), sizeof(PcapGlobalHeader));
        if (!file) {
            std::cerr << "Hata: PCAP Global Header okunamadi." << std::endl;
            return false;
        }

        std::cout << "[SUCCESS] PCAP dosyasi basariyla acildi!" << std::endl;
        return true;
    }

    // Bir sonraki paketin basligini ve verisini okur
    bool readNextPacket(PcapPacketHeader& packetHeader, std::vector<char>& packetBuffer) {
        if (!file || file.eof()) return false;

        // Paket Basligini Oku (16 Bytes)
        file.read(reinterpret_cast<char*>(&packetHeader), sizeof(PcapPacketHeader));
        if (file.gcount() < sizeof(PcapPacketHeader)) return false;

        // Paketin icerik boyutuna gore tamponu (buffer) boyutlandir
        packetBuffer.resize(packetHeader.inclLen);

        // Paket icerigini oku
        file.read(packetBuffer.data(), packetHeader.inclLen);
        return file.gcount() == packetHeader.inclLen;
    }

    void close() {
        if (file.is_open()) {
            file.close();
            std::cout << "PCAP dosyasi kapatildi." << std::endl;
        }
    }

    ~PcapReader() {
        close();
    }
};

#endif // PCAP_READER_H