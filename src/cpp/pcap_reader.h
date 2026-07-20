#ifndef PCAP_READER_H
#define PCAP_READER_H

#include <iostream>
#include <fstream>
#include <string>
#include "itch_messages.h"

class PcapReader {
private:
    std::ifstream file;
    PcapGlobalHeader globalHeader;

public:
    // PCAP dosyasini binary modda acan fonksiyon
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
        std::cout << "Magic Number: 0x" << std::hex << globalHeader.magicNumber << std::dec << std::endl;
        return true;
    }

    // Dosyayı kapatan fonksiyon
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