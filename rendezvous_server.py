"""
PeerSync Rendezvous Server
---------------------------
Minimal, self-hostable peer discovery service.

Design constraints (from threat model, Section 5 of the report):
  - Stores ONLY transient connection metadata: peer_id -> (ip, port, last_seen)
  - NEVER sees file content, encryption keys, or file metadata
  - Compromise of this server must not expose synchronised data
  - Entries expire automatically (default: 60s) so stale peers vanish
    without needing an explicit "goodbye" message (handles crashes,
    laptop sleep, network drops, etc.)

HTTP endpoints (metadata store):
  POST /register   { "peer_id": "...", "port": 5000 }
      -> registers the caller. IP is taken from the request itself
         (request.remote_addr), NOT from the client-supplied body.
         This matters: if you trusted a client-supplied IP, any peer
         could register spoofed entries and redirect connections
         elsewhere.
      -> "port" should be the peer's PUBLIC UDP port as learned from
         the STUN-style reflector below, not an arbitrary local port
         — see NAT_TRAVERSAL note.

  GET  /peer/<peer_id>
      -> returns {"peer_id", "ip", "port", "last_seen"} or 404 if
         unknown / expired.

  GET  /peers
      -> debug/testing endpoint listing all currently live peers.

UDP endpoint (STUN-style address reflector, NAT_TRAVERSAL):
  Any UDP packet sent to --stun-port gets a reply containing the
  ip:port the packet APPEARED to come from, as seen from outside the
  sender's NAT. A client can't know its own public address any other
  way — its own OS only knows its private LAN address. This is the
  same trick STUN/WebRTC use. The client must send this UDP probe
  from the *same local socket* it intends to use for the peer-to-peer
  hole-punch attempt (see punch_client.py), otherwise the NAT hands
  out a different public port for each socket and the discovered
  address is useless.

Run:
    pip install flask
    python3 rendezvous_server.py --port 8000 --stun-port 8001

Client integration (matches Phase 2 of the implementation plan):
    1. Open a UDP socket, probe --stun-port to learn your public
       ip:port, then POST /register with that public port.
       Re-register every ~30s (must beat the 60s TTL).
    2. Before attempting to reach a group peer, GET /peer/<id> to
       fetch its current public ip:port.
    3. UDP hole-punch to that address for ~10s (see punch_client.py);
       on failure, fall back to the relay server. The rendezvous
       server plays no part in that decision — it only ever hands
       out addresses.
"""

import argparse
import socket
import threading
import time

from flask import Flask, jsonify, request

app = Flask(__name__)

# peer_id -> {"ip": str, "port": int, "last_seen": float}
_peers: dict[str, dict] = {}
_lock = threading.Lock()

TTL_SECONDS = 60
CLEANUP_INTERVAL_SECONDS = 15


@app.post("/register")
def register():
    body = request.get_json(silent=True) or {}
    peer_id = body.get("peer_id")
    port = body.get("port")

    if not peer_id or not isinstance(port, int):
        return jsonify(error="peer_id (str) and port (int) are required"), 400

    ip = request.remote_addr  # trust the transport, not the payload

    with _lock:
        _peers[peer_id] = {"ip": ip, "port": port, "last_seen": time.time()}

    return jsonify(status="registered", peer_id=peer_id, ip=ip, port=port), 200


@app.get("/peer/<peer_id>")
def get_peer(peer_id):
    with _lock:
        entry = _peers.get(peer_id)

    if entry is None:
        return jsonify(error="unknown or expired peer_id"), 404

    return jsonify(peer_id=peer_id, **entry), 200


@app.get("/peers")
def list_peers():
    with _lock:
        snapshot = {pid: dict(v) for pid, v in _peers.items()}
    return jsonify(snapshot), 200


def _cleanup_loop():
    """Background thread: evict entries older than TTL_SECONDS."""
    while True:
        time.sleep(CLEANUP_INTERVAL_SECONDS)
        cutoff = time.time() - TTL_SECONDS
        with _lock:
            expired = [pid for pid, v in _peers.items() if v["last_seen"] < cutoff]
            for pid in expired:
                del _peers[pid]


def _stun_reflector_loop(host: str, port: int):
    """
    Minimal STUN-style reflector: reply to every UDP packet with the
    sender's own (ip, port) as seen from outside their NAT. This is
    how a peer discovers its own public address before hole-punching.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f" * STUN reflector listening on udp://{host}:{port}")

    while True:
        data, addr = sock.recvfrom(1024)
        ip, port_ = addr
        reply = f"{ip}:{port_}".encode()
        sock.sendto(reply, addr)


def main():
    parser = argparse.ArgumentParser(description="PeerSync rendezvous server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000, help="HTTP port for register/lookup")
    parser.add_argument("--stun-port", type=int, default=8001, help="UDP port for address reflection")
    args = parser.parse_args()

    threading.Thread(target=_cleanup_loop, daemon=True).start()
    threading.Thread(
        target=_stun_reflector_loop, args=(args.host, args.stun_port), daemon=True
    ).start()
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()