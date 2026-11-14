#!/usr/bin/env python3
"""Replay original Crossword UI keys and environment ports against one index."""
from __future__ import annotations

import ast
import copy
import json
import os
import random
import runpy
from collections import deque
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = Path(os.environ.get("NW_ORIGINAL_SOURCE_ROOT", ROOT.parent / "original-neural-workshop-enhanced"))
reference = runpy.run_path(str(ROOT / "test/crossword_diff.py"), run_name="crossword_reference")
fixture = [
    ("one", 36), ("may", 48), ("sea", 806), ("play", 853),
    ("ask", 919), ("key", 995), ("mary", 1453), ("lee", 2495),
    ("mom", 5042), ("prey", 8081), ("ana", 9505), ("ally", 9859),
]
slip_count = int(os.environ.get("NW_CROSSWORD_SLIPS", "1"))
assert slip_count >= 1
if os.environ.get("NW_CROSSWORD_LEXICON"):
    index_text = Path(os.environ["NW_CROSSWORD_LEXICON"]).read_text(encoding="utf-8")
else:
    index_text = "".join(f"{word}\t{rank}\tFixture clue for {word}\n" for word, rank in fixture)
if os.environ.get("NW_CROSSWORD_REVERSE") == "1":
    index_text = "".join(reversed(index_text.splitlines(keepends=True)))
entries = []
for line in index_text.splitlines():
    fields = line.split("\t")
    if len(fields) == 3:
        word, rank, clue = fields
        if int(rank) < 10000 and 3 <= len(word) <= 6:
            entries.append(reference["Entry"](word, int(rank), clue))
lexicon = reference["Lexicon"](sorted(entries, key=lambda entry: entry.rank))
ref = reference["REF"]

def generate(level, seed):
    return ref["deal_one"](ref["grade_of"](level), random.Random(seed), lexicon)

key = SimpleNamespace(SPACE=1, ESCAPE=2, F11=3, TAB=4, UP=5, DOWN=6,
                      LEFT=7, RIGHT=8, BACKSPACE=9, DELETE=10,
                      **{letter: 100 + index for index, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")})
methods = {"clamped", "size", "_reset", "start_run", "_next_trial", "slot_here",
           "clue_line", "blocked", "given", "move", "turn", "write", "erase",
           "_step_on", "wrong", "_settle", "_solved", "_finish", "score",
           "on_key_press", "click"}
tree = ast.parse((ORIGINAL / "neural_workshop/ui/crossword.py").read_text(encoding="utf-8"))
original_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Crossword")
selected = [copy.deepcopy(node) for node in original_class.body
            if isinstance(node, ast.FunctionDef) and node.name in methods]
module = ast.Module(body=[ast.ClassDef(name="SourceCrossword", bases=[], keywords=[],
                                      body=selected, decorator_list=[])], type_ignores=[])
ast.fix_missing_locations(module)
space = {"GRADES": ref["GRADES"], "grade_of": ref["grade_of"], "generate": generate,
         "LETTERS": "abcdefghijklmnopqrstuvwxyz", "key": key,
         "pyglet": SimpleNamespace(event=SimpleNamespace(EVENT_HANDLED=1)),
         "display": SimpleNamespace(toggle_fullscreen=lambda: None), "_": lambda value: value}
exec(compile(module, "original-crossword-ui", "exec", flags=__import__("__future__").annotations.compiler_flag), space)
SourceCrossword = space["SourceCrossword"]
SourceCrossword.stocked = staticmethod(lambda: True)

env_tree = ast.parse((ORIGINAL / "nwenv/crossword.py").read_text(encoding="utf-8"))
env_class = next(node for node in env_tree.body if isinstance(node, ast.ClassDef) and node.name == "CrosswordEnv")
drive = next(copy.deepcopy(node) for node in env_class.body if isinstance(node, ast.FunctionDef) and node.name == "drive")
env_module = ast.Module(body=[ast.ClassDef(name="SourceEnv", bases=[], keywords=[], body=[drive], decorator_list=[])], type_ignores=[])
ast.fix_missing_locations(env_module)
env_space = {"STEPS": ((0, -1), (0, 1), (-1, 0), (1, 0)),
             "LETTERS": "abcdefghijklmnopqrstuvwxyz", "ERASE": 30}
exec(compile(env_module, "original-crossword-env", "exec", flags=__import__("__future__").annotations.compiler_flag), env_space)
env = env_space["SourceEnv"]()

class Verdict:
    def clear(self): pass
    def show(self, good, message): self.last = (good, message)

def make_ui():
    ui = SourceCrossword.__new__(SourceCrossword)
    ui.rng = random.Random(17)
    ui.start_rung = ui.rung = 2
    ui.total_trials = 1
    ui.show_mistakes = ui.adaptive = True
    ui.puzzle = None
    ui.filled = []
    ui.at = 0
    ui.down = False
    ui.trial = 0
    ui.results = []
    ui.phase = "ready"
    ui.message = "Press Space to start"
    ui.verdict_shown = None
    ui.verdict = Verdict()
    ui._redraw = lambda: None
    ui.now_ms = 1000
    ui.clock = lambda: ui.now_ms / 1000.0
    return ui

ui, env_ui = make_ui(), make_ui()
phase = {"ready": 0, "solving": 1, "solved": 2, "done": 3}

def snapshot(task):
    puzzle = task.puzzle
    score = task.score()
    verdict = -1 if task.verdict_shown is None else int(bool(task.verdict_shown[0]))
    slips = task.mistakes if puzzle is not None else 0
    last_seconds = int(task.results[-1][2]) if task.results else 0
    state = [phase[task.phase], task.rung, task.trial, task.total_trials,
             puzzle.size if puzzle else 0, len(puzzle.slots) if puzzle else 0,
             task.at if puzzle else 0, int(task.down) if puzzle else 0,
             verdict, score["solved"], slips,
             int(task.message == "Full, but not right yet"), 1,
             int(task.show_mistakes), int(task.adaptive), score["slips"],
             score["best_rung"], score["clean"], score["seconds"], last_seconds]
    cells = [] if puzzle is None else [
        [ord(letter) if letter else 0,
         ord(task.filled[at]) if task.filled[at] else 0,
         int(at in puzzle.givens)]
        for at, letter in enumerate(puzzle.solution)]
    clue = task.clue_line() if puzzle is not None and task.phase == "solving" else ""
    return {"state": state, "cells": cells, "message": task.message, "clue": clue}

trace = []
ports = {"up": (0, key.UP, 4), "down": (1, key.DOWN, 5),
         "left": (2, key.LEFT, 2), "right": (3, key.RIGHT, 3),
         "erase": (30, key.BACKSPACE, 8), "turn": (31, key.TAB, 6)}

def send(kind, value=0, delay=10):
    ui.now_ms += delay
    env_ui.now_ms = ui.now_ms
    if kind == "start":
        prior = env_ui.phase
        ui.on_key_press(key.SPACE, 0)
        env_ui._next_trial() if prior == "solved" else env_ui.start_run()
        action, action_value, result = 0, 0, 1
    elif kind == "click":
        ui.click(value)
        env_ui.click(value)
        action, action_value = 9, value
        result = 2 if ui.blocked(value) else 1
    elif kind == "write":
        ui.on_key_press(getattr(key, value.upper()), 0)
        env.drive(env_ui, 4 + ord(value) - 97)
        action, action_value, result = 7, ord(value) - 97, 1
    else:
        port, symbol, action = ports[kind]
        ui.on_key_press(symbol, 0)
        env.drive(env_ui, port)
        action_value, result = 0, 1
    expected = snapshot(ui)
    assert snapshot(env_ui) == expected, f"original UI and Env diverged on {kind}"
    trace.append({"action": action, "value": action_value, "now": ui.now_ms,
                  "result": result, **expected})

def move_to(target):
    if ui.at == target:
        return
    size = ui.size()
    paths = {ui.at: []}
    queue = deque([ui.at])
    while queue:
        current = queue.popleft()
        x, y = current % size, current // size
        for name, dx, dy in (("up", 0, -1), ("down", 0, 1), ("left", -1, 0), ("right", 1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < size and 0 <= ny < size:
                cell = ny * size + nx
                if cell not in paths and not ui.blocked(cell):
                    paths[cell] = paths[current] + [name]
                    queue.append(cell)
    assert target in paths
    for name in paths[target]:
        send(name)

send("start", delay=0)
assert ui.phase == "solving" and ui.puzzle.blocks
blocked = min(ui.puzzle.blocks)
send("click", blocked)
given = min(ui.puzzle.givens)
move_to(given)
send("write", "z")
wrong = next(cell for cell, letter in enumerate(ui.puzzle.solution)
             if letter and cell not in ui.puzzle.givens)
move_to(wrong)
send("turn")
wrong_letters = [letter for letter in "xyz" if letter != ui.puzzle.solution[wrong]]
for index in range(slip_count):
    move_to(wrong)
    send("write", wrong_letters[index % len(wrong_letters)])
for cell, letter in enumerate(ui.puzzle.solution):
    if not letter or cell in ui.puzzle.givens or cell == wrong:
        continue
    move_to(cell)
    send("write", letter)
assert ui.phase == "solving" and ui.message == "Full, but not right yet"
move_to(wrong)
send("erase")
send("write", ui.puzzle.solution[wrong], delay=2501)
assert ui.phase == "solved" and ui.mistakes == slip_count
send("start")
assert ui.phase == "done"
send("start")
print(json.dumps({"index": index_text, "trace": trace}, ensure_ascii=False))
