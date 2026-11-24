#!/usr/bin/env python3
"""Exercise word-task corpus creation through the window-free SDL binary."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

binary = Path(sys.argv[1])
for flag in ('--scramble-index', '--scramble-sentences'):
    result = subprocess.run([str(binary), flag], capture_output=True, text=True, timeout=15)
    assert result.returncode == 2 and f'Expected a value for {flag}' in result.stderr
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    env = os.environ.copy()
    env['APPDATA' if os.name == 'nt' else 'HOME'] = directory
    def run(task, index='-', sentences='-'):
        result = subprocess.run([str(binary), '--selftest-word-corpus', task, str(index), str(sentences)],
                                env=env, capture_output=True, text=True, check=True, timeout=15)
        return result.stdout.strip()
    missing = root / 'missing'
    bad, index, sentences = root / 'bad', root / 'lexicon.tsv', root / 'sentences.txt'
    bad.write_bytes(b'bad')
    index.write_bytes(b'cat\t1\t\na\t2\t\naaa\t3\tThree-letter clue\n')
    sentences.write_bytes(b'a cat a cat a cat\n')
    for task in ('crossword', 'scrabble'):
        assert run(task) == '1'
        assert run(task, missing) == '0'
        assert run(task, bad) == '0'
        assert run(task, index) == '1'
    assert run('scramble', missing) == '0'
    assert run('scramble', '-', missing) == '0'
    assert run('scramble') == '1 0 0'
    assert run('scramble', index) == '1 1 0'
    assert run('scramble', '-', sentences) == '1 0 1'
    assert run('scramble', index, sentences) == '1 1 1'
    relative = ('Brain Workshop/data/words' if os.name == 'nt' else
                'Library/Application Support/Brain Workshop/data/words' if sys.platform == 'darwin' else
                '.brainworkshop/data/words')
    default_dir = root / relative
    default_dir.mkdir(parents=True)
    for length, expected in ((4096, '1 0 0'), (4097, '1 0 1')):
        (default_dir / 'sentences.txt').write_bytes((b'a cat a cat a cat\n' * 300)[:length])
        assert run('scramble') == expected
print('SDL word corpus: controller creation, error handling, and fallback boundary pass')
