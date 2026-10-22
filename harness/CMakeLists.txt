cmake_minimum_required(VERSION 3.20)
project(ditto_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(ditto_cpp
    src/main.cpp
    src/agent.cpp
    src/store.cpp
    src/retrieval.cpp
    src/network.cpp
    src/embedding.cpp
    src/local_helpers.cpp
    src/lane.cpp
    src/surface.cpp
    src/deliberation.cpp
    src/short.cpp
    src/records_advice.cpp
    src/output.cpp
)
target_include_directories(ditto_cpp PRIVATE include)
target_compile_options(ditto_cpp PRIVATE -O2 -Wall -Wextra -Wpedantic)
target_link_libraries(ditto_cpp PRIVATE sqlite3 curl crypto pthread cpp-httplib icuuc icui18n)

add_executable(store_smoke tests/store_smoke.cpp src/store.cpp)
target_include_directories(store_smoke PRIVATE include)
target_link_libraries(store_smoke PRIVATE sqlite3 crypto pthread)

add_executable(local_helpers_smoke tests/local_helpers_smoke.cpp src/local_helpers.cpp)
target_include_directories(local_helpers_smoke PRIVATE include)
target_link_libraries(local_helpers_smoke PRIVATE crypto pthread icuuc icui18n)

add_executable(short_smoke tests/short_smoke.cpp src/short.cpp src/output.cpp)
target_include_directories(short_smoke PRIVATE include)
target_link_libraries(short_smoke PRIVATE crypto pthread icuuc)

add_executable(output_smoke tests/output_smoke.cpp src/output.cpp)
target_include_directories(output_smoke PRIVATE include)
target_link_libraries(output_smoke PRIVATE icuuc)

add_executable(network_smoke tests/network_smoke.cpp src/network.cpp)
target_include_directories(network_smoke PRIVATE include)
target_link_libraries(network_smoke PRIVATE curl pthread)

add_executable(embedding_smoke tests/embedding_smoke.cpp)
target_include_directories(embedding_smoke PRIVATE include)
target_link_libraries(embedding_smoke PRIVATE curl pthread)

add_executable(agent_control_smoke tests/agent_control_smoke.cpp)
target_include_directories(agent_control_smoke PRIVATE include)

add_executable(retrieval_smoke tests/retrieval_smoke.cpp src/retrieval.cpp src/lane.cpp)
target_include_directories(retrieval_smoke PRIVATE include)
target_link_libraries(retrieval_smoke PRIVATE crypto pthread icuuc icui18n)
