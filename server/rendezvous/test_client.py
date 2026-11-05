"""
PeerSync Rendezvous Client (rendezvous steps only, no peer-to-peer)
-------------------------------------------------------------------
Does exactly three things, then reports the result:

  1. Probe the server's UDP reflector to learn this device's public ip:port.
  2. Register that public port with the rendezvous server (HTTP).
  3. Look up another peer's registered address and print it.

It does NOT try to connect to the other peer. That belongs to the
peer-to-peer part of PeerSync.

Usage:
    python3 rendezvous_client.py --server http://EC2_IP:8000 \
        --stun-server EC2_IP --stun-port 8001 \
        --peer-id alice --local-port 6001 --target bob

Add --keep-alive to re-register every 30s (the server expires entries
after 60s) and keep looking up the target until Ctrl+C.
"""

import argparse
import socket
import time

import requests

REGISTER_INTERVAL = 5


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
        print(f"[reflect]  Public address: {public_ip}:{public_port}")

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