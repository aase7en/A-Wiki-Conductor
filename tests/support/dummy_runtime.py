"""Self-owned loopback dummy runtime used only by Stage A integration tests."""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class ReadyHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if self.path == "/readyz":
            body = b"ready\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--marker", required=True)
    args = parser.parse_args()

    state_path = Path(args.state_file)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    server = ThreadingHTTPServer(("127.0.0.1", 0), ReadyHandler)
    state_path.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "port": int(server.server_address[1]),
                "marker": args.marker,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    server.serve_forever(poll_interval=0.05)


if __name__ == "__main__":
    main()
