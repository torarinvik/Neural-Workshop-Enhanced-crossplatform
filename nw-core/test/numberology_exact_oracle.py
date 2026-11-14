#!/usr/bin/env python3
"""Create/check original Numberology fixtures for public-controller replay."""
import argparse
import json
import random
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'original-neural-workshop-enhanced'))
from neural_workshop import numberology
fixture = Path(__file__).with_name('numberology_exact_oracle.json')
cases = []
for level in (1, 3, 5, 6, 7, 40, 200, 1000, 3000, 10000):
    seed = 19
    deal_seed = random.Random(seed).randrange(1 << 30)
    puzzle = numberology.generate(level, deal_seed)
    cases.append({'level': level, 'seed': seed, 'terms': list(map(str, puzzle.terms)),
                  'answer': str(puzzle.answer), 'rule': puzzle.rule})
expected = json.dumps(cases, indent=2) + '\n'
parser = argparse.ArgumentParser()
parser.add_argument('--check', action='store_true')
if parser.parse_args().check:
    if fixture.read_text() != expected:
        raise SystemExit('Numberology exact fixture differs from source')
    print(f'Numberology source fixtures: {len(cases)} cases match')
else:
    fixture.write_text(expected)
