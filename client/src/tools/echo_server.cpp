#include "../net/socket_utils.h"

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
    int sockfd = listen_tcp6(PORT);

    if (sockfd == -1) {
        std::cerr << "Failed to listen on port " << PORT << '\n';
        return 1;
    }

    std::cout << "Listening on port " << PORT << "...\n";

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
