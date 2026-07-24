cmake_minimum_required(VERSION 3.14)
project(bist_lob_analysis CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(lob_engine src/cpp/main.cpp)

# PostgreSQL konumu makineye göre bulunur. Gerekirse CMake'i şu şekilde
# çalıştırın: cmake -DPostgreSQL_ROOT="C:/Program Files/PostgreSQL/18" ..
find_package(PostgreSQL REQUIRED)

target_include_directories(lob_engine PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src/cpp
    ${PostgreSQL_INCLUDE_DIRS}
)

target_link_libraries(lob_engine PRIVATE ${PostgreSQL_LIBRARIES})
if (WIN32)
    target_link_libraries(lob_engine PRIVATE ws2_32)
endif()
