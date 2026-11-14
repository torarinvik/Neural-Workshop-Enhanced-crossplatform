#!/usr/bin/env python3
"""Verify shared Scramble settings across Python and SDL processes."""
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
    os.environ['NW_SCRAMBLE_SETTINGS_PATH'] = str(path)
    def sdl(*args):
        return subprocess.run([str(binary), *args], check=True, capture_output=True, text=True).stdout.strip()
    assert sdl('--selftest-scramble-settings-read') == '3 5 1 1'
    subprocess.run([str(binary), '--selftest-scramble-settings-write'], check=True)
    assert app.read_scramble_settings() == (12, 15, 0, 1)
    app.write_scramble_settings((4, 5, 1, 0))
    assert sdl('--selftest-scramble-settings-read') == '4 5 1 0'
    assert sdl('--selftest-scramble-settings-read', '--scramble-level', '12') == '12 5 1 0'
    for invalid in ('1 4 1 1\n', '1 3 2 1\n', '9999999999999999999999999 3 1 1\n', '1 3 1 1 extra\n'):
        path.write_text(invalid)
        assert app.read_scramble_settings() == (3, 5, 1, 1)
        assert sdl('--selftest-scramble-settings-read') == '3 5 1 1'
if os.name != 'nt':
    with tempfile.TemporaryDirectory() as home:
        env = os.environ.copy()
        env.pop('NW_SCRAMBLE_SETTINGS_PATH', None)
        env['HOME'] = home
        for _ in range(2):
            subprocess.run([str(binary), '--selftest-scramble-settings-write'], env=env, check=True)
        assert (Path(home) / '.neural-workshop/scramble-options').read_text().strip() == '12 15 0 1'
        result = subprocess.run([sys.executable, '-c',
            'import sys; sys.path.insert(0, sys.argv[1]); import app; print(app.read_scramble_settings())',
            str(root / 'shells/python')], env=env, check=True, capture_output=True, text=True)
        assert result.stdout.strip() == '(12, 15, 0, 1)'
print('scramble_native_settings_test: PASS (shared persistence, CLI precedence, invalid data)')
