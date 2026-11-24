#!/usr/bin/env python3
"""Verify persisted settings interoperability and invalid-file fallback."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'shells/python'))
import app
binary = Path(os.environ.get('NW_SDL_BINARY', root / 'build/nw-sdl3'))
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'settings'
    os.environ['NW_CROSSWORD_SETTINGS_PATH'] = str(path)
    def sdl(*args):
        return subprocess.run([str(binary), *args], check=True, capture_output=True, text=True).stdout.strip()
    assert sdl('--selftest-crossword-settings-read') == '2 3 1 1'
    subprocess.run([str(binary), '--selftest-crossword-settings-write'], check=True)
    assert app.read_crossword_settings() == (7, 8, 0, 1)
    app.write_crossword_settings((4, 5, 1, 0))
    assert sdl('--selftest-crossword-settings-read') == '4 5 1 0'
    assert sdl('--selftest-crossword-settings-read', '--crossword-level', '10') == '10 5 1 0'
    for invalid in ('1 4 1 1\n', '1 3 2 1\n', '9999999999999999999999999 3 1 1\n', '1 3 1 1 extra\n'):
        path.write_text(invalid)
        assert app.read_crossword_settings() == (2, 3, 1, 1)
        assert sdl('--selftest-crossword-settings-read') == '2 3 1 1'
if os.name != 'nt':
    with tempfile.TemporaryDirectory() as home:
        env = os.environ.copy()
        env.pop('NW_CROSSWORD_SETTINGS_PATH', None)
        env['HOME'] = home
        # A fresh profile must create the directory, and subsequent saves must replace the file.
        for _ in range(2):
            subprocess.run([str(binary), '--selftest-crossword-settings-write'], env=env, check=True)
        path = Path(home) / '.neural-workshop/crossword-options'
        assert path.read_text().strip() == '7 8 0 1'
        result = subprocess.run([sys.executable, '-c',
            'import sys; sys.path.insert(0, sys.argv[1]); import app; print(app.read_crossword_settings())',
            str(root / 'shells/python')], env=env, check=True, capture_output=True, text=True)
        assert result.stdout.strip() == '(7, 8, 0, 1)'
print('crossword_native_settings_test: PASS (restart, shared file, CLI precedence, invalid data)')
