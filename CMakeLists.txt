cmake_minimum_required(VERSION 3.14)
project(bist_lob_analysis CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# C++ Kaynak dosyalarının yolu
include_directories(src/cpp)

# PostgreSQL 18 kütüphane ve başlık dosyaları
include_directories("C:/Program Files/PostgreSQL/18/include")
link_directories("C:/Program Files/PostgreSQL/18/lib")

# Ana çalıştırılabilir dosya
add_executable(lob_engine src/cpp/main.cpp)

# PostgreSQL libpq bağlantısı
target_link_libraries(lob_engine PRIVATE libpq)