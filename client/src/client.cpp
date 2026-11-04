#include "net/socket_utils.h"

#include <iostream>
#include <string>

#include <arpa/inet.h>
#include <cerrno>
#include <cstdio>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

const char* PORT = "5000";
const char* HOST = "::1"; // localhost

int main() {
    addrinfo hints{};
    addrinfo* res = nullptr;

    hints.ai_family = AF_INET6;      // IPv6
    hints.ai_socktype = SOCK_STREAM; // TCP

    int status = getaddrinfo(HOST, PORT, &hints, &res);

    if (status != 0) {
        std::cerr << "getaddrinfo error: " << gai_strerror(status) << '\n';
        return 1;
    }
    std::cout << "getaddrinfo success\n";

    int sockfd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);

    if (sockfd == -1) {
        std::perror("socket error");
        freeaddrinfo(res);
        return 1;
    }
    std::cout << "socket created\n";

    if (connect(sockfd, res->ai_addr, res->ai_addrlen) == -1) {
        std::perror("connect error");
        close(sockfd);
        freeaddrinfo(res);
        return 1;
    }
    std::cout << "connected to server\n";

    freeaddrinfo(res); // free the linked list

    std::string message;

    std::cout << "Enter message: ";
    std::getline(std::cin, message);

    message += '\n'; // add newline to message

    if (!send_all(sockfd, message.c_str(), message.size())) {
        std::perror("send_all error");
        close(sockfd);
        return 1;
    }

    std::cout << "server replied: ";

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

        std::cout.write(buffer, bytes_received);

        bool done = false;

        for (ssize_t i = 0; i < bytes_received; i++) {
            if (buffer[i] == '\n') {
                done = true;
                break;
            }
        }

        if (done)
            break;
    }

    close(sockfd);
    return 0;
}