#include "socket_utils.h"

#include <cerrno>
#include <cstdio>
#include <iostream>
#include <netdb.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

bool send_all(int fd, const char* data, size_t len) {
    size_t sent = 0; // track how many bytes have been sent

    while (sent < len) {
        ssize_t n = send(fd, data + sent, len - sent, MSG_NOSIGNAL);
        // data + sent points to remaining unsent data
        // len - sent is the number of bytes left to send
        // MSG_NOSIGNAL prevents  SIGPIPE  from terminating your process if the peer
        // disconnects

        if (n == -1) {
            if (errno == EINTR) // interrupted by signal, try again
                continue;

            return false;
        }

        if (n == 0)
            return false;

        sent += static_cast<size_t>(n);
    }

    return true;
}

bool recv_all(int fd, char* buf, size_t len) {
    size_t received = 0; // track how many bytes have been received

    while (received < len) {
        ssize_t n = recv(fd, buf + received, len - received, 0);
        // buf + received points to remaining space in buffer
        // len - received is the number of bytes left to receive

        if (n == -1) {
            if (errno == EINTR) // interrupted by signal, try again
                continue;

            return false;
        }

        if (n == 0)
            return false; // connection closed

        received += static_cast<size_t>(n);
    }

    return true;
}

int connect_tcp6(const char* host, const char* port) {
    addrinfo hints{};
    addrinfo* res = nullptr;

    hints.ai_family = AF_INET6;      // IPv6
    hints.ai_socktype = SOCK_STREAM; // TCP

    int status = getaddrinfo(host, port, &hints, &res);

    if (status != 0) {
        std::cerr << "getaddrinfo error: " << gai_strerror(status) << '\n';
        return -1;
    }

    int sockfd = -1;

    for (addrinfo* ai = res; ai != nullptr; ai = ai->ai_next) {
        sockfd = socket(ai->ai_family, ai->ai_socktype, ai->ai_protocol);

        if (sockfd == -1) {
            continue;
        }

        if (connect(sockfd, ai->ai_addr, ai->ai_addrlen) == 0) {
            // Successfully connected
            break;
        }

        close(sockfd);
        sockfd = -1;
    }

    freeaddrinfo(res);
    return sockfd;
}

int listen_tcp6(const char* port) {
    addrinfo hints{};
    addrinfo* res = nullptr;

    hints.ai_family = AF_INET6;      // IPv6
    hints.ai_socktype = SOCK_STREAM; // TCP
    hints.ai_flags = AI_PASSIVE;     // For wildcard IP address

    int status = getaddrinfo(nullptr, port, &hints, &res);

    if (status != 0) {
        std::cerr << "getaddrinfo error: " << gai_strerror(status) << '\n';
        return -1;
    }

    int sockfd = -1;

    for (addrinfo* ai = res; ai != nullptr; ai = ai->ai_next) {
        sockfd = socket(ai->ai_family, ai->ai_socktype, ai->ai_protocol);

        if (sockfd == -1) {
            continue;
        }

        int opt = 1;
        int v6only = 1;

        if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) == -1 ||
            setsockopt(sockfd, IPPROTO_IPV6, IPV6_V6ONLY, &v6only, sizeof(v6only)) == -1) {
            std::perror("setsockopt");
            close(sockfd);
            sockfd = -1;
            continue;
        }

        if (bind(sockfd, ai->ai_addr, ai->ai_addrlen) == -1) {
            std::perror("bind");
            close(sockfd);
            sockfd = -1;
            continue;
        }

        if (listen(sockfd, 5) == -1) {
            std::perror("listen");
            close(sockfd);
            sockfd = -1;
            continue;
        }

        break; // Successfully bound and listening
    }

    freeaddrinfo(res);
    return sockfd;
}