"""Exercise the packaged ESC-50 downloader with a real local HTTP server."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.parse import parse_qs, urlsplit
import wave


def fixture_pcm():
    output = BytesIO()
    with wave.open(output, "wb") as writer:
        writer.setparams((1, 2, 44100, 0, "NONE", "not compressed"))
        writer.writeframes(b"\x00\x10\x00\xf0" * 100)
    return output.getvalue()


def verify(binary):
    pcm = fixture_pcm()
    requests = []
    unavailable = False

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, payload, mime):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            parsed = urlsplit(self.path)
            requests.append(parsed.path)
            if parsed.path == "/rows":
                query = parse_qs(parsed.query)
                assert query["dataset"] == ["renumics/esc50"]
                assert query["config"] == ["default"] and query["split"] == ["train"]
                assert query["length"] == ["100"]
                offset = int(query["offset"][0])
                assert offset % 100 == 0 and 0 <= offset < 2000
                if unavailable:
                    self.reply(503, b"offline", "text/plain")
                    return
                origin = f"http://127.0.0.1:{self.server.server_port}"
                rows = [
                    {"row_idx": offset + 100, "row": {"audio": {"src": f"{origin}/unexpected"}}},
                    {"row_idx": offset, "row": {"audio": {"src": f"{origin}/bad-wave"}}},
                    {"row_idx": offset + 1, "row": {"audio": {"src": f"{origin}/missing"}}},
                    {"row_idx": offset + 2, "row": {"audio": []}},
                ]
                for index in range(3, 12):
                    cells = [{}, {"src": f"{origin}/audio/{offset + index}", "type": "audio/wav"}]
                    rows.append({"row_idx": offset + index, "row": {"audio": cells}})
                self.reply(200, json.dumps({"rows": rows}).encode(), "application/json")
            elif parsed.path == "/bad-wave":
                self.reply(200, b"<html>not a recording</html>", "text/html")
            elif parsed.path.startswith("/audio/"):
                self.reply(200, pcm, "audio/wav")
            else:
                self.reply(404, b"missing", "text/plain")

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server, TemporaryDirectory() as temp:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            profile = Path(temp) / "new-profile"
            bank = profile / "datasets" / "esc50"
            env = dict(os.environ, NW_ESC50_ROWS_URL=f"http://127.0.0.1:{server.server_port}/rows",
                       SDL_VIDEODRIVER="nw-invalid-driver")
            args = [str(binary), "--datadir", str(profile), "--fetch-esc50"]

            def fetch(wanted):
                return subprocess.run([*args, str(wanted)], env=env, capture_output=True,
                                      text=True, timeout=45)

            assert fetch(2001).returncode == 2
            assert not profile.exists()
            first = fetch(3)
            assert first.returncode == 0, (first.stdout, first.stderr)
            files = sorted(bank.iterdir())
            assert len(files) == 3 and all(path.read_bytes() == pcm for path in files), files
            assert all(int(path.stem) % 100 in range(3, 12) and len(path.name) == 11 for path in files)
            count = len(requests)
            same = fetch(3)
            assert same.returncode == 0 and len(requests) == count, (same.stdout, same.stderr)
            topped = fetch(5)
            assert topped.returncode == 0, (topped.stdout, topped.stderr)
            assert len(list(bank.glob("*.wav"))) == 5 and all(path.read_bytes() == pcm for path in files)
            assert "/unexpected" not in requests and "/bad-wave" in requests and "/missing" in requests
            unavailable = True
            stopped = fetch(6)
            assert stopped.returncode == 1 and "incomplete" in stopped.stderr.lower(), stopped.stderr
            assert len(list(bank.iterdir())) == 5
        finally:
            server.shutdown()
            thread.join()


if __name__ == "__main__":
    verify(Path(sys.argv[1]).resolve())
    print("PASS: SDL ESC-50 fetch validates WAVs, resumes existing banks, and preserves files on HTTP failure")
