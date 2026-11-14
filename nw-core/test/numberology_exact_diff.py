#!/usr/bin/env python3
"""Compare lossless sequence terms with the original, including >64-bit cases."""
import subprocess
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'original-neural-workshop-enhanced'))
from neural_workshop import numberology as ref
from numberology_diff import rule_fields
rows = subprocess.check_output([sys.argv[1]], text=True).splitlines()
assert len(rows) == 52, len(rows)
large = 0
for row in rows:
    level, seed, shown, rule, a, b, c, complexity, payload = row.split('|')
    level, seed = int(level), int(seed)
    puzzle = ref.generate(level, seed)
    values = [int(value) for value in payload.split(',')]
    expected = [*puzzle.terms, puzzle.answer]
    assert values == expected, (level, seed, values, expected)
    assert (int(shown), int(rule), int(a), int(b), int(c), int(complexity)) == (
        len(puzzle.terms), *rule_fields(puzzle.rule), puzzle.complexity)
    large += any(abs(value) > 2**63 - 1 for value in expected)
assert large >= 12, large
print(f'PASS: {len(rows)} cases identical, {large} exceed signed 64-bit')
