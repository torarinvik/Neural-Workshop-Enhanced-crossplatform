#!/usr/bin/env python3
"""Verify shared Scrabble settings across Python and SDL processes."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app
binary = root / 'build/nw-sdl3'
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'settings'
    os.environ['NW_SCRABBLE_SETTINGS_PATH'] = str(path)
    def sdl(*args):
        return subprocess.run([str(binary), *args], check=True, capture_output=True, text=True).stdout.strip()
    assert sdl('--selftest-scrabble-settings-read') == '3 5 1 1'
    subprocess.run([str(binary), '--selftest-scrabble-settings-write'], check=True)
    assert app.read_scrabble_settings() == (7, 15, 0, 1)
    app.write_scrabble_settings((4, 5, 1, 0))
    assert sdl('--selftest-scrabble-settings-read') == '4 5 1 0'
    assert sdl('--selftest-scrabble-settings-read', '--scrabble-level', '10') == '10 5 1 0'
    for invalid in ('1 4 1 1\n', '1 3 2 1\n', '9999999999999999999999999 3 1 1\n', '1 3 1 1 extra\n'):
        path.write_text(invalid)
        assert app.read_scrabble_settings() == (3, 5, 1, 1)
        assert sdl('--selftest-scrabble-settings-read') == '3 5 1 1'
if os.name != 'nt':
    with tempfile.TemporaryDirectory() as home:
        env = os.environ.copy()
        env.pop('NW_SCRABBLE_SETTINGS_PATH', None)
        env['HOME'] = home
        for _ in range(2):
            subprocess.run([str(binary), '--selftest-scrabble-settings-write'], env=env, check=True)
        assert (Path(home) / '.neural-workshop/scrabble-options').read_text().strip() == '7 15 0 1'
        result = subprocess.run([sys.executable, '-c',
            'import sys; sys.path.insert(0, sys.argv[1]); import app; print(app.read_scrabble_settings())',
            str(root / 'shells/python')], env=env, check=True, capture_output=True, text=True)
        assert result.stdout.strip() == '(7, 15, 0, 1)'
print('scrabble_native_settings_test: PASS (shared persistence, CLI precedence, invalid data)')
