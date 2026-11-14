#!/usr/bin/env python3
"""Regenerate/check original-Python Algebra working fixtures for WASM replay."""
import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'original-neural-workshop-enhanced'))
from neural_workshop import algebra  # noqa: E402

fixture = Path(__file__).with_name('algebra_working_oracle.json')
cases = []
for seed in (5, 19, 41, 97):
    for level in range(1, 13):
        question_seed = random.Random(seed).randrange(1 << 30)
        problem = algebra.generate(level, seed=question_seed)
        if problem is None:
            raise RuntimeError(f'original generator failed: {level=}, {seed=}')
        cases.append(dict(seed=seed, level=level, asked=problem.asked,
                          working='\n'.join(problem.working)))
expected = json.dumps(cases, ensure_ascii=False, indent=2) + '\n'
parser = argparse.ArgumentParser()
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
if args.check:
    if fixture.read_text() != expected:
        raise SystemExit('Algebra working fixture differs from original Python')
    print(f'Algebra original working fixtures: {len(cases)} cases match')
else:
    fixture.write_text(expected)
