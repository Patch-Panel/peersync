import argparse
import socket
import time

import requests

REGISTER_INTERVAL = 30


def discover_public_address(sock, stun_host, stun_port):
    sock.sendto(b"who-am-i", (stun_host, stun_port))
    sock.settimeout(5)
    data, _ = sock.recvfrom(1024)
    ip, port_str = data.decode().rsplit(":", 1)
    return ip, int(port_str)


def register(server, peer_id, public_port):
    resp = requests.post(
        f"{server}/register",
        json={"peer_id": peer_id, "port": public_port},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()


def lookup(server, peer_id):
    resp = requests.get(f"{server}/peer/{peer_id}", timeout=5)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    body = resp.json()
    return body["ip"], body["port"]


def main():
    p = argparse.ArgumentParser(description="PeerSync rendezvous client")
    p.add_argument("--server", required=True, help="e.g. http://EC2_IP:8000")
    p.add_argument("--stun-server", required=True, help="plain IP/host of the reflector")
    p.add_argument("--stun-port", type=int, required=True)
    p.add_argument("--peer-id", required=True)
    p.add_argument("--local-port", type=int, required=True)
    p.add_argument("--target", required=True, help="peer_id to look up")
    p.add_argument("--keep-alive", action="store_true")
    args = p.parse_args()

    # One UDP socket, kept open so the NAT mapping stays valid.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", args.local_port))

    while True:
        public_ip, public_port = discover_public_address(sock, args.stun_server, args.stun_port)
        print(f"[reflect]  my public address as seen by the server: {public_ip}:{public_port}")

        reg = register(args.server, args.peer_id, public_port)
        print(f"[register] stored as {reg['ip']}:{reg['port']}")

        found = lookup(args.server, args.target)
        if found:
            print(f"[lookup]   {args.target} -> {found[0]}:{found[1]}")
        else:
            print(f"[lookup]   {args.target} is not registered (offline or expired)")

        if not args.keep_alive:
            break
        time.sleep(REGISTER_INTERVAL)


if __name__ == "__main__":
    main()