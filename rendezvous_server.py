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

Endpoints:
  POST /register   { "peer_id": "...", "port": 5000 }
      -> registers the caller. IP is taken from the request itself
         (request.remote_addr), NOT from the client-supplied body.
         This matters: if you trusted a client-supplied IP, any peer
         could register spoofed entries and redirect connections
         elsewhere. Only the port is client-supplied, since the
         server can't know which local port the peer is listening on.

  GET  /peer/<peer_id>
      -> returns {"peer_id", "ip", "port", "last_seen"} or 404 if
         unknown / expired.

  GET  /peers
      -> debug/testing endpoint listing all currently live peers.

Run:
    pip install flask
    python3 rendezvous_server.py --port 8000

Client integration (matches Phase 2 of the implementation plan):
    1. On startup, and every ~30s thereafter, POST /register to keep
       the entry alive (must re-register before the 60s TTL expires).
    2. Before attempting to reach a group peer, GET /peer/<id> to
       fetch its current ip:port.
    3. Attempt a direct TCP connection for ~10s; on failure, fall
       back to the relay server. The rendezvous server plays no part
       in that decision — it only ever hands out addresses.
"""

import argparse
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


def main():
    parser = argparse.ArgumentParser(description="PeerSync rendezvous server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    threading.Thread(target=_cleanup_loop, daemon=True).start()
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()