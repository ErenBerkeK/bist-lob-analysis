#include <iostream>
#include "itch_messages.h"

int main() {
    std::cout << "--- BIST LOB Engine Struct Boyut Yapilari ---" << std::endl;
    std::cout << "PcapHeader: " << sizeof(PcapGlobalHeader) << " bytes" << std::endl;
    std::cout << "AddOrder:   " << sizeof(AddOrderMessage) << " bytes" << std::endl;
    std::cout << "Executed:   " << sizeof(OrderExecutedMessage) << " bytes" << std::endl;
    std::cout << "Cancel:     " << sizeof(OrderCancelMessage) << " bytes" << std::endl;
    std::cout << "Delete:     " << sizeof(OrderDeleteMessage) << " bytes" << std::endl;
    return 0;
}