#!/usr/bin/env bash
# Serve the web shell over HTTP. Firefox will not fetch the WASM binary from a
# file:// page, so opening shells/web/index.html directly leaves it loading.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${NW_WEB_PORT:-8000}"
cd "$ROOT"
echo "Open http://127.0.0.1:${PORT}/shells/web/index.html"
if [[ "${NW_WEB_SHARED_FRAMES:-0}" == 1 ]]; then
    exec python3 - "$PORT" <<'PYTHON'
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import sys


class IsolatedHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()


with ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), IsolatedHandler) as server:
    server.serve_forever()
PYTHON
fi
exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$ROOT"
