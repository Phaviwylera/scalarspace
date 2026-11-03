#!/usr/bin/env python3
"""Serve Scalar Lab V6 on loopback only; standard library, no dependencies."""
from __future__ import annotations
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import webbrowser

ROOT = Path(__file__).resolve().parent


class LocalHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()

    def log_message(self, fmt: str, *args: object) -> None:
        # Keep the local console readable; HTTP errors are still reported by the handler.
        if args and str(args[1] if len(args) > 1 else "").startswith("4"):
            super().log_message(fmt, *args)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local Scalar Lab V6 dashboard")
    parser.add_argument("--port", type=int, default=8765, help="preferred local port (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="do not open a browser automatically")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    handler = partial(LocalHandler, directory=str(ROOT))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError:
        if args.port == 0:
            raise
        print(f"Port {args.port} is unavailable; selecting a free local port.")
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
    print("Scalar Lab V6 is running locally.")
    print(f"Open: {url}")
    print("The server listens on 127.0.0.1 only. Press Ctrl+C to stop.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Scalar Lab V6.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
