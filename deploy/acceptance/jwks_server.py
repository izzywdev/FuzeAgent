#!/usr/bin/env python3
"""Minimal JWKS endpoint for the A2A acceptance gate.

Serves the ephemeral JWKS produced by ``gen_test_identity.py`` at the Keycloak-style
path the server's ``runtime._build_verifier`` fetches
(``<issuer>/protocol/openid-connect/certs``). Any GET returns the JWKS; a tiny
``/healthz`` lets the workflow wait until it is up. Stdlib only — no server deps.

    python jwks_server.py --jwks /tmp/jwks.json --host 127.0.0.1 --port 9099
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def build_handler(jwks_bytes: bytes):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path.rstrip("/").endswith("healthz"):
                self._send(b"ok", "text/plain")
                return
            self._send(jwks_bytes, "application/json")

        def _send(self, body: bytes, content_type: str):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # keep CI logs quiet
            return

    return Handler


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jwks", required=True)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9099)
    args = ap.parse_args()

    jwks_bytes = json.dumps(json.loads(Path(args.jwks).read_text(encoding="utf-8"))).encode("utf-8")
    server = ThreadingHTTPServer((args.host, args.port), build_handler(jwks_bytes))
    print(f"jwks_server listening on http://{args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
