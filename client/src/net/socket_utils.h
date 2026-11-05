#ifndef SOCKET_UTILS_H
#define SOCKET_UTILS_H

#include <cstddef>

bool send_all(int fd, const char* data, size_t length);
bool recv_all(int fd, char* buffer, size_t length);

int connect_tcp6(const char* host, const char* port);
int listen_tcp6(const char* port);

#endif // SOCKET_UTILS_H