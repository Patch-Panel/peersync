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