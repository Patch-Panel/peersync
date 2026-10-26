"""
PeerSync UDP Hole-Punch Client
--------------------------------
Demonstrates the full NAT traversal sequence:
 
  1. Open ONE UDP socket, bound to a local port.
  2. Probe the rendezvous server's STUN reflector from that socket to
     learn our own public ip:port (what the outside world sees).
  3. Register that public port with the rendezvous server (HTTP).
  4. Look up the target peer's public ip:port (HTTP).
  5. From the SAME socket, repeatedly send "PUNCH" packets to the
     peer's public address while also listening for incoming ones.
     The first packet from each side opens a hole in its own NAT;
     once both holes are open, packets flow both ways and the
     connection is "up".
 
Usage:
    # peer "alice"
    python3 punch_client.py --server http://127.0.0.1:8000 \
        --stun-server 127.0.0.1 --stun-port 8001 \
        --peer-id alice --local-port 6001 --target bob
 
    # peer "bob"
    python3 punch_client.py --server http://127.0.0.1:8000 \
        --stun-server 127.0.0.1 --stun-port 8001 \
        --peer-id bob --local-port 6002 --target alice
 
Note: run alice and bob from two DIFFERENT networks to actually
exercise NAT traversal. Running both on localhost/LAN will "succeed"
trivially since there's no NAT in the way — that only proves the
message flow is correct, not that hole punching itself works.
"""
 
import argparse
import socket
import time
 
import requests
 
 
def discover_public_address(sock: socket.socket, stun_host: str, stun_port: int) -> tuple[str, int]:
    sock.sendto(b"who-am-i", (stun_host, stun_port))
    sock.settimeout(5)
    data, _ = sock.recvfrom(1024)
    ip, port_str = data.decode().rsplit(":", 1)
    return ip, int(port_str)
 
 
def register(server: str, peer_id: str, public_port: int) -> None:
    resp = requests.post(f"{server}/register", json={"peer_id": peer_id, "port": public_port}, timeout=5)
    resp.raise_for_status()
    print(f"[register] {resp.json()}")
 
 
def lookup(server: str, peer_id: str) -> tuple[str, int] | None:
    resp = requests.get(f"{server}/peer/{peer_id}", timeout=5)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    body = resp.json()
    return body["ip"], body["port"]
 
 
def punch(sock: socket.socket, target_addr: tuple[str, int], peer_id: str, timeout: float = 10.0) -> bool:
    sock.settimeout(0.5)
    deadline = time.time() + timeout
    message = f"PUNCH:{peer_id}".encode()
 
    while time.time() < deadline:
        sock.sendto(message, target_addr)
        try:
            data, addr = sock.recvfrom(1024)
            print(f"[punch]    received {data!r} from {addr} -> hole open!")
            # Send a couple of acks so the other side's loop also exits cleanly.
            sock.sendto(f"PUNCH-ACK:{peer_id}".encode(), target_addr)
            return True
        except socket.timeout:
            continue
 
    return False
 
 
def main():
    parser = argparse.ArgumentParser(description="PeerSync UDP hole-punch client")
    parser.add_argument("--server", required=True, help="rendezvous HTTP base URL")
    parser.add_argument("--stun-server", required=True)
    parser.add_argument("--stun-port", type=int, required=True)
    parser.add_argument("--peer-id", required=True)
    parser.add_argument("--local-port", type=int, required=True)
    parser.add_argument("--target", required=True, help="peer_id to hole-punch to")
    parser.add_argument("--punch-timeout", type=float, default=10.0)
    args = parser.parse_args()
 
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", args.local_port))
 
    public_ip, public_port = discover_public_address(sock, args.stun_server, args.stun_port)
    print(f"[stun]     my public address is {public_ip}:{public_port}")
 
    register(args.server, args.peer_id, public_port)
 
    print(f"[lookup]   waiting for '{args.target}' to register...")
    target = None
    while target is None:
        target = lookup(args.server, args.target)
        if target is None:
            time.sleep(1)
    print(f"[lookup]   {args.target} -> {target}")
 
    ok = punch(sock, target, args.peer_id, timeout=args.punch_timeout)
 
    if ok:
        print(f"\n✅ Direct connection to {args.target} established via hole punching.")
    else:
        print(f"\n❌ Hole punch to {args.target} failed after {args.punch_timeout}s "
              f"(likely symmetric NAT) — fall back to the relay server here.")
 
 
if __name__ == "__main__":
    main()