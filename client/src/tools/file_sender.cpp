
#include "../net/socket_utils.h"

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <vector>

#include <unistd.h>

constexpr const char* HOST = "::1";
constexpr const char* PORT = "5001";
constexpr size_t BUFFER_SIZE = 64 * 1024;

int main() {
    const char* filename = "test.bin";

    std::ifstream file(filename, std::ios::binary);

    if (!file) {
        std::cerr << "could not open file\n";
        return 1;
    }

    std::error_code ec;
    uint64_t file_size = std::filesystem::file_size(filename, ec);

    if (ec) {
        std::cerr << "could not determine file size\n";
        return 1;
    }

    int sockfd = connect_tcp6(HOST, PORT);

    if (sockfd == -1) {
        std::cerr << "could not connect to receiver\n";
        return 1;
    }

    std::cout << "connected to receiver\n";

    // Encode file size as an 8-byte big-endian integer.
    char header[8];
    uint64_t size = file_size;

    for (int i = 7; i >= 0; --i) {
        header[i] = static_cast<char>(size & 0xFF);
        size >>= 8;
    }

    if (!send_all(sockfd, header, sizeof(header))) {
        std::cerr << "failed to send file size\n";
        close(sockfd);
        return 1;
    }

    std::vector<char> buffer(BUFFER_SIZE);
    uint64_t remaining = file_size;

    while (remaining > 0) {
        size_t chunk_size = static_cast<size_t>(std::min<uint64_t>(buffer.size(), remaining));

        file.read(buffer.data(), static_cast<std::streamsize>(chunk_size));

        if (file.gcount() != static_cast<std::streamsize>(chunk_size)) {
            std::cerr << "failed to read file chunk\n";
            close(sockfd);
            return 1;
        }

        if (!send_all(sockfd, buffer.data(), chunk_size)) {
            std::cerr << "failed to send file chunk\n";
            close(sockfd);
            return 1;
        }

        remaining -= chunk_size;
    }

    std::cout << "sent " << file_size << " bytes\n";

    close(sockfd);
    return 0;
}
