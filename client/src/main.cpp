#include "net/socket_utils.h"

#include <iostream>

#include <arpa/inet.h>
#include <cerrno>
#include <cstdio>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

const char* PORT = "5000";
const int BACKLOG = 5; // pending connections

int main() {
    addrinfo hints{};
    addrinfo* res = nullptr;

    hints.ai_family = AF_INET6;      // IPv6
    hints.ai_socktype = SOCK_STREAM; // TCP
    hints.ai_flags = AI_PASSIVE;     // use my IP

    int status = getaddrinfo(nullptr, PORT, &hints, &res);

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
    std::cout << "socket created, fd: " << sockfd << '\n';

    int opt = 1;

    if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) == -1) {
        perror("setsockopt");
        close(sockfd);
        freeaddrinfo(res);
        return 1;
    }

    int v6only = 1;
    if (setsockopt(sockfd, IPPROTO_IPV6, IPV6_V6ONLY, &v6only, sizeof(v6only)) == -1) {
        std::perror("setsockopt error");
        close(sockfd);
        freeaddrinfo(res);
        return 1;
    }
    std::cout << "setsockopt success\n";

    if (bind(sockfd, res->ai_addr, res->ai_addrlen) == -1) {
        std::perror("bind error");
        close(sockfd);
        freeaddrinfo(res);
        return 1;
    }
    std::cout << "socket bound\n";

    freeaddrinfo(res); // free the linked list

    if (listen(sockfd, BACKLOG) == -1) {
        std::perror("listen error");
        close(sockfd);
        return 1;
    }
    std::cout << "listening on port " << PORT << '\n';

    sockaddr_storage client_addr{};
    socklen_t client_addrlen = sizeof(client_addr);

    int client_fd = accept(sockfd, reinterpret_cast<sockaddr*>(&client_addr), &client_addrlen);

    if (client_fd == -1) {
        std::perror("accept error");
        close(sockfd);
        return 1;
    }
    std::cout << "client connected, fd: " << client_fd << '\n';

    char host[INET6_ADDRSTRLEN];

    auto* a = reinterpret_cast<sockaddr_in6*>(&client_addr);

    if (inet_ntop(AF_INET6, &a->sin6_addr, host, sizeof(host)) == nullptr) {
        std::perror("inet_ntop");
    } else {
        std::cout << "client " << host << " port " << ntohs(a->sin6_port) << '\n';
    }

    char buffer[1024];

    while (true) {
        ssize_t bytes_received = recv(client_fd, buffer, sizeof(buffer), 0);

        if (bytes_received == -1) {
            if (errno == EINTR)
                continue;

            std::perror("recv");
            break;
        }

        else if (bytes_received == 0) {
            std::cout << "client disconnected\n";
            break;
        }

        std::cout << "received " << bytes_received << " bytes\n";
        std::cout.write(buffer, bytes_received);
        std::cout << '\n';

        if (!send_all(client_fd, buffer, static_cast<size_t>(bytes_received))) {
            std::perror("send error");
            break;
        }
    }

    close(client_fd);
    close(sockfd);
}
