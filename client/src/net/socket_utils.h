#ifndef SOCKET_UTILS_H
#define SOCKET_UTILS_H

#include <cstddef>

bool send_all(int fd, const char* data, size_t length);

#endif // SOCKET_UTILS_H