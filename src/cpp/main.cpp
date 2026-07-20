#include <iostream>
#include "pcap_reader.h"

int main() {
    std::cout << "=== BIST LOB PCAP Reader Test ===" << std::endl;

    PcapReader reader;
    // data klasörü altındaki test.pcap dosyasını açmayı dener
    if (reader.open("data/test.pcap")) {
        std::cout << "Dosya okumaya hazir." << std::endl;
    } else {
        std::cout << "Not: 'data/test.pcap' bulunamadi. Gercek .pcap dosyasini data/ klasorune ekleyecegiz." << std::endl;
    }

    return 0;
}