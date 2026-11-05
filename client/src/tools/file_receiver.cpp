
#include "../net/socket_utils.h"

#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <vector>

#include <sys/socket.h>
#include <unistd.h>

constexpr const char* PORT = "5001";
constexpr size_t BUFFER_SIZE = 64 * 1024;

int main() {
    int server_fd = listen_tcp6(PORT);

    if (server_fd == -1) {
        std::cerr << "failed to start receiver\n";
        return 1;
    }

    std::cout << "listening on port " << PORT << '\n';

    int client_fd = accept(server_fd, nullptr, nullptr);

    if (client_fd == -1) {
        std::perror("accept");
        close(server_fd);
        return 1;
    }

    std::cout << "sender connected\n";

    // Receive the 8-byte file size header.
    char header[8];

    if (!recv_all(client_fd, header, sizeof(header))) {
        std::cerr << "failed to receive file size\n";
        close(client_fd);
        close(server_fd);
        return 1;
    }

    // Decode the big-endian integer.
    uint64_t file_size = 0;

    for (int i = 0; i < 8; ++i) {
        file_size = (file_size << 8) | static_cast<unsigned char>(header[i]);
    }

    std::cout << "incoming file size: " << file_size << " bytes\n";

    std::ofstream file("received.bin", std::ios::binary);

    if (!file) {
        std::cerr << "could not create received.bin\n";
        close(client_fd);
        close(server_fd);
        return 1;
    }

    std::vector<char> buffer(BUFFER_SIZE);
    uint64_t remaining = file_size;

    while (remaining > 0) {
        size_t chunk_size = static_cast<size_t>(std::min<uint64_t>(buffer.size(), remaining));

        if (!recv_all(client_fd, buffer.data(), chunk_size)) {
            std::cerr << "incomplete or failed receive\n";
            close(client_fd);
            close(server_fd);
            return 1;
        }

        file.write(buffer.data(), static_cast<std::streamsize>(chunk_size));

        if (!file) {
            std::cerr << "failed to write file chunk\n";
            close(client_fd);
            close(server_fd);
            return 1;
        }

        remaining -= chunk_size;
    }

    file.close();

    if (!file) {
        std::cerr << "failed to finish writing file\n";
        close(client_fd);
        close(server_fd);
        return 1;
    }

    std::cout << "received and saved " << file_size << " bytes\n";

    close(client_fd);
    close(server_fd);

    return 0;
}
