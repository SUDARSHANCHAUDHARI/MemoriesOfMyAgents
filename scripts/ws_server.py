#!/usr/bin/env python3
"""
WebSocket server for real-time observation streaming.
Pure stdlib — no extra dependencies.
Runs on ws://localhost:7842

Start: python3 scripts/ws_server.py [port]
Dashboard connects via WebSocket and receives live observation events.
"""
import hashlib
import http
import json
import os
import select
import socket
import struct
import sys
import threading
import time
from base64 import b64encode
from pathlib import Path

PROJECT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from moma.config import MOMA_ROOT

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 7842
RAW_DIR = MOMA_ROOT / "raw"

# ── WebSocket handshake ───────────────────────────────────────────────────────

WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _ws_accept_key(key: str) -> str:
    import hashlib
    from base64 import b64encode
    return b64encode(hashlib.sha1((key + WS_MAGIC).encode()).digest()).decode()


def _handshake(conn: socket.socket, request: bytes) -> bool:
    lines = request.decode(errors="replace").split("\r\n")
    headers = {}
    for line in lines[1:]:
        if ": " in line:
            k, _, v = line.partition(": ")
            headers[k.lower()] = v
    key = headers.get("sec-websocket-key", "")
    if not key:
        return False
    accept = _ws_accept_key(key)
    response = (
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
    )
    conn.sendall(response.encode())
    return True


def _send_text(conn: socket.socket, text: str) -> bool:
    data = text.encode()
    length = len(data)
    if length < 126:
        header = bytes([0x81, length])
    elif length < 65536:
        header = struct.pack("!BBH", 0x81, 126, length)
    else:
        header = struct.pack("!BBQ", 0x81, 127, length)
    try:
        conn.sendall(header + data)
        return True
    except Exception:
        return False


# ── Client handler ────────────────────────────────────────────────────────────

clients: list[socket.socket] = []
clients_lock = threading.Lock()


def handle_client(conn: socket.socket, addr):
    # Read HTTP upgrade request
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = conn.recv(1024)
        if not chunk:
            conn.close()
            return
        buf += chunk

    if not _handshake(conn, buf):
        conn.close()
        return

    with clients_lock:
        clients.append(conn)

    print(f"[moma-ws] client connected: {addr}", flush=True)

    try:
        while True:
            # Just keep connection alive — we only push, not read
            ready = select.select([conn], [], [], 10)
            if ready[0]:
                data = conn.recv(1024)
                if not data:
                    break
    except Exception:
        pass
    finally:
        with clients_lock:
            if conn in clients:
                clients.remove(conn)
        conn.close()
        print(f"[moma-ws] client disconnected: {addr}", flush=True)


def broadcast(message: str):
    with clients_lock:
        dead = []
        for conn in clients:
            if not _send_text(conn, message):
                dead.append(conn)
        for conn in dead:
            clients.remove(conn)
            try:
                conn.close()
            except Exception:
                pass


# ── File watcher thread ───────────────────────────────────────────────────────

def watch_raw():
    seen: set[str] = set()

    # Seed existing
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for f in RAW_DIR.glob("*.jsonl"):
        try:
            for line in f.read_text().splitlines():
                if line.strip():
                    try:
                        seen.add(json.loads(line)["id"])
                    except Exception:
                        pass
        except Exception:
            pass

    while True:
        time.sleep(0.5)
        try:
            for f in RAW_DIR.glob("*.jsonl"):
                for line in f.read_text().splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obs = json.loads(line)
                        if obs.get("id") not in seen:
                            seen.add(obs["id"])
                            broadcast(json.dumps(obs))
                    except Exception:
                        pass
        except Exception:
            pass


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    threading.Thread(target=watch_raw, daemon=True).start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", PORT))
    server.listen(20)

    print(f"[moma-ws] WebSocket server on ws://localhost:{PORT}", flush=True)
    print(f"[moma-ws] watching {RAW_DIR}", flush=True)

    while True:
        try:
            conn, addr = server.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
        except KeyboardInterrupt:
            print("\n[moma-ws] stopping", flush=True)
            server.close()
            break
        except Exception as e:
            print(f"[moma-ws] error: {e}", flush=True)


if __name__ == "__main__":
    main()
