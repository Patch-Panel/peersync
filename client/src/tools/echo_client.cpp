#include "../net/socket_utils.h"

#include <cstring>
#include <iostream>
#include <string>

#include <cerrno>
#include <cstdio>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

constexpr const char* DEFAULT_HOST = "::1";
constexpr const char* DEFAULT_PORT = "5000";

int main(int argc, char* argv[]) {
    if (argc > 3) {
        std::cerr << "Usage: " << argv[0] << " [host] [port]\n";
        return 1;
    }

    const char* host = (argc >= 2) ? argv[1] : DEFAULT_HOST;
    const char* port = (argc == 3) ? argv[2] : DEFAULT_PORT;

    int sockfd = connect_tcp6(host, port);

    if (sockfd == -1) {
        std::cerr << "Failed to connect to " << host << ":" << port << '\n';
        return 1;
    }

    std::cout << "Connected to " << host << ":" << port << '\n';

    std::string message;

    std::cout << "Enter message: ";
    std::getline(std::cin, message);

    message += '\n'; // add newline to message

    if (!send_all(sockfd, message.c_str(), message.size())) {
        std::perror("send_all error");
        close(sockfd);
        return 1;
    }

    char buffer[1024];

    while (true) {
        ssize_t bytes_received = recv(sockfd, buffer, sizeof(buffer), 0);

        if (bytes_received == -1) {
            if (errno == EINTR)
                continue;

            std::perror("recv");
            break;
        }

        else if (bytes_received == 0) {
            std::cout << "server disconnected\n";
            break;
        }
        std::cout << "server replied: ";
        std::cout.write(buffer, bytes_received);

        bool done = false;

        if (memchr(buffer, '\n', static_cast<size_t>(bytes_received)) != nullptr) {
            break;
        }

        if (done)
            break;
    }

    close(sockfd);
    return 0;
}