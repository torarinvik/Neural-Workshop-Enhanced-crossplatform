#!/usr/bin/env bash
# Serve the web shell over HTTP. Firefox will not fetch the WASM binary from a
# file:// page, so opening shells/web/index.html directly leaves it loading.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${NW_WEB_PORT:-8000}"
cd "$ROOT"
echo "Open http://127.0.0.1:${PORT}/shells/web/index.html"
exec python3 -m http.server "$PORT" --bind 127.0.0.1 --directory "$ROOT"
