"""
PeerSync Rendezvous Test Client
--------------------------------
Simulates one peer's registration + lookup behaviour so you can test
the rendezvous server without building the full sync daemon yet.

Usage examples:

  # Terminal 1: run the server (from the other file)
  python3 rendezvous_server.py --port 8000

  # Terminal 2: act as "alice", listening (pretend) on port 5001,
  # re-registering every 20s, and looking up "bob" every 10s
  python3 test_client.py --server http://127.0.0.1:8000 \
      --peer-id alice --port 5001 --lookup bob

  # Terminal 3: act as "bob"
  python3 test_client.py --server http://127.0.0.1:8000 \
      --peer-id bob --port 5002 --lookup alice

Watch alice's terminal start printing 404s (bob not registered yet),
then flip to showing bob's ip:port once bob's client starts up.
Kill bob's client (Ctrl+C) and watch alice's lookups go back to 404
about 60 seconds later, once bob's entry expires.
"""

import argparse
import time

import requests


def register(server: str, peer_id: str, port: int) -> None:
    resp = requests.post(
        f"{server}/register",
        json={"peer_id": peer_id, "port": port},
        timeout=5,
    )
    resp.raise_for_status()
    print(f"[register] {resp.json()}")


def lookup(server: str, peer_id: str) -> None:
    resp = requests.get(f"{server}/peer/{peer_id}", timeout=5)
    if resp.status_code == 404:
        print(f"[lookup]   {peer_id} -> not found (offline or expired)")
    else:
        resp.raise_for_status()
        print(f"[lookup]   {peer_id} -> {resp.json()}")


def main():
    parser = argparse.ArgumentParser(description="PeerSync rendezvous test client")
    parser.add_argument("--server", required=True, help="e.g. http://127.0.0.1:8000")
    parser.add_argument("--peer-id", required=True, help="this peer's id, e.g. alice")
    parser.add_argument("--port", type=int, required=True, help="port this peer 'listens on'")
    parser.add_argument("--lookup", help="peer_id of another peer to repeatedly look up")
    parser.add_argument("--register-interval", type=float, default=20.0)
    parser.add_argument("--lookup-interval", type=float, default=10.0)
    args = parser.parse_args()

    last_register = 0.0
    last_lookup = 0.0

    print(f"Starting as '{args.peer_id}' on port {args.port}. Ctrl+C to stop.\n")

    try:
        while True:
            now = time.time()

            if now - last_register >= args.register_interval or last_register == 0.0:
                register(args.server, args.peer_id, args.port)
                last_register = now

            if args.lookup and (now - last_lookup >= args.lookup_interval or last_lookup == 0.0):
                lookup(args.server, args.lookup)
                last_lookup = now

            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
