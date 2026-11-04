cmake_minimum_required(VERSION 3.20)

project(PeerSync LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(ps_server
    client/src/main.cpp
    client/src/net/socket_utils.cpp
)

add_executable(ps_client
    client/src/client.cpp
    client/src/net/socket_utils.cpp
)