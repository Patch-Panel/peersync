#include "socket_utils.h"

#include <cerrno>
#include <sys/socket.h>

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