#!/usr/bin/env python3
"""Replay original Numberology controller methods without opening a window."""
import argparse
import ast
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

root = Path(__file__).resolve().parents[2]
original = root / 'original-neural-workshop-enhanced'
sys.path.insert(0, str(original))
from neural_workshop.numberology import generate, is_correct

source = original / 'neural_workshop/ui/numberology.py'
tree = ast.parse(source.read_text())
cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Numberology')
methods = {'clamped', '_reset', 'start_run', '_next_trial', '_finish', 'write', 'erase', 'submit', 'advance'}
cls.body = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in methods]
module = ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[]))
namespace = {'generate': generate, 'is_correct': is_correct, '_': lambda value: value,
             'state': SimpleNamespace(cfg={})}
exec(compile(module, str(source), 'exec'), namespace)
Controller = namespace['Numberology']

class Verdict:
    def clear(self): pass
    def show(self, *_): pass

cases = []
for level, seed, trials, adaptive, answers in ((1, 17, 1, True, (True,)),
                                                (1, 23, 1, True, (True,)),
                                                (1, 19, 3, True, (True, True, True)),
                                                (7, 42, 3, True, (True, False, True)),
                                                (40, 11, 2, False, (True, True))):
    ui = Controller.__new__(Controller)
    ui.rng = random.Random(seed)
    ui.clock = lambda: 2.0
    ui.start_difficulty = level
    ui.total_trials = trials
    ui.advance_on_perfect = adaptive
    ui.verdict = Verdict()
    ui._redraw = lambda: None
    ui._reset()
    ui.advance()
    rows = []
    for correct in answers:
        puzzle = ui.puzzle
        ui.submit()  # empty input is ignored
        assert ui.phase == 'working'
        answer = str(puzzle.answer if correct else puzzle.answer + 1)
        for char in answer: ui.write(char)
        ui.submit()
        rows.append({'terms': [str(value) for value in puzzle.terms], 'answer': str(puzzle.answer),
                     'rule': puzzle.rule, 'input': answer, 'message': ui.message,
                     'right': sum(result[1] for result in ui.results)})
        ui.advance()
    cases.append({'level': level, 'seed': seed, 'trials': trials, 'adaptive': adaptive,
                  'rows': rows, 'message': ui.message, 'next_level': ui.start_difficulty})
expected = json.dumps(cases, indent=2, ensure_ascii=False) + '\n'
path = Path(__file__).with_name('numberology_session_oracle.json')
parser = argparse.ArgumentParser()
parser.add_argument('--check', action='store_true')
if parser.parse_args().check:
    if path.read_text() != expected: raise SystemExit('Numberology session oracle differs from original')
    print('Numberology source sessions: mixed and perfect runs match')
else:
    path.write_text(expected)
