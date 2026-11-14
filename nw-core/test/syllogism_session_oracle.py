#!/usr/bin/env python3
"""Source-derived Syllogism sessions with independent per-question seeds."""
import argparse
import json
import random
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'original-neural-workshop-enhanced'))
from neural_workshop import syllogism

cases = []
for level in range(1, 13):
    rng = random.Random(17)
    rows = []
    for trial in range(2):
        seed = rng.randrange(1 << 30)
        question = syllogism.generate(level, seed=seed, made_up=False)
        if question is None:
            raise SystemExit(f'source could not generate level {level} seed {seed}')
        rows.append({'seed': seed, 'lines': list(question.lines), 'asked': question.asked,
                     'options': list(question.options), 'answer': question.answer,
                     'working': list(question.working), 'grade': question.grade.name})
    cases.append({'level': level, 'seed': 17, 'rows': rows})
made_up_cases = []
for level in (1, 7, 9, 12):
    seed = random.Random(17).randrange(1 << 30)
    question = syllogism.generate(level, seed=seed, made_up=True)
    if question is None: raise SystemExit(f'source could not generate invented-word level {level}')
    made_up_cases.append({'level': level, 'lines': list(question.lines), 'asked': question.asked,
                          'options': list(question.options), 'answer': question.answer})
made_up_expected = json.dumps(made_up_cases, ensure_ascii=False, indent=2) + '\n'
made_up_path = Path(__file__).with_name('syllogism_madeup_oracle.json')
expected = json.dumps(cases, ensure_ascii=False, indent=2) + '\n'
path = Path(__file__).with_name('syllogism_session_oracle.json')
parser = argparse.ArgumentParser()
parser.add_argument('--check', action='store_true')
if parser.parse_args().check:
    if path.read_text() != expected or made_up_path.read_text() != made_up_expected:
        raise SystemExit('Syllogism sessions differ from source')
    print(f'Syllogism source sessions: {len(cases)} levels match')
else:
    path.write_text(expected)
    made_up_path.write_text(made_up_expected)
