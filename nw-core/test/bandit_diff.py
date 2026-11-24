"""Compare Explore or Exploit's deals, fading reference, and par with Python."""
from pathlib import Path
from random import Random
import subprocess
import sys
from types import SimpleNamespace

import pyglet

pyglet.options.shadow_window = False
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import bandit
from neural_workshop.ui.bandit import ExploreOrExploit


def compare(rows, name, values, where):
    label, *fields = next(rows).split()
    assert label == name and len(fields) == len(values), (where, label, fields, values)
    result = tuple((float(field) if isinstance(value, float) else int(field))
                   for field, value in zip(fields, values))
    assert result == tuple(values), (where, name, result, values)


rows = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
payouts = 0
for rung in (0, 1, 3, 4, 5, 6, 7, 9, 10, 12, 13, 16, 19, 20, 25, 35):
    for index in range(4):
        seed = 17 + index * 31337
        run = bandit.deal(rung, seed=-seed) if index % 2 == 0 else bandit.deal(rung, rng=Random(seed))
        compare(rows, "grade", run.level, (rung, seed))
        policy = bandit.reference_policy(run)
        chosen = []
        for turn, pays in enumerate(run.pays):
            shown = bandit.seen_after(run, turn)
            history = [[] for _ in range(run.level.arms)]
            for pull in range(shown):
                arm = chosen[pull]
                history[arm].append((pull, run.pays[pull][arm]))
            arm = policy(history, turn, chosen)
            where = (rung, seed, turn)
            compare(rows, "turn", (arm, shown), where)
            chosen.append(arm)
            for mean, pay in zip(run.means[turn], pays):
                compare(rows, "pay", (mean, pay), where)
                payouts += 1
        compare(rows, "scores", (bandit.reference(run), bandit.floor(run), bandit.best(run),
                                 bandit.par(run)), (rung, seed))
class Screen(ExploreOrExploit):
    def __init__(self):
        self.rng = Random(-17)
        self.start_rung = 16
        self.total_trials = 2
        self.adaptive = True
        self.now = 0
        self.clock = lambda: self.now / 1000
        self.verdict = SimpleNamespace(show=lambda *_: None, clear=lambda: None)
        self.last_pass = False

    def _redraw(self):
        pass

    def _judge(self, passed, message):
        self.last_pass = passed
        super()._judge(passed, message)


screen = Screen()
screen.start_run()


def state(accepted):
    score = screen.score()
    phase = {"ready": 0, "playing": 1, "judged": 2, "done": 3}[screen.phase]
    coins = screen.coins(everything=phase == 2) if screen.run else 0
    compare(rows, "session", (int(accepted), phase, screen.rung, screen.trial, len(screen.chosen),
                              coins, int(screen.last_pass), score["passed"], score["best_rung"],
                              screen.par), screen.now)


state(True)
for trial in range(2):
    screen.pull(7)
    state(False)
    policy = bandit.reference_policy(screen.run)
    while screen.phase == "playing":
        turn = len(screen.chosen)
        history = [[] for _ in range(screen.run.level.arms)]
        for pull in range(bandit.seen_after(screen.run, turn)):
            arm = screen.chosen[pull]
            history[arm].append((pull, screen.run.pays[pull][arm]))
        arm = policy(history, turn, screen.chosen) if not trial else 0
        screen.now += 1
        screen.pull(arm)
        state(True)
    screen.now += 2999
    screen.update(0)
    state(False)
    screen.now += 1
    screen.update(0)
    state(True)
screen.now += 1
screen.start_run()
state(True)
assert next(rows, None) is None
print(f"PASS: 64 Explore or Exploit deals and {payouts} means and payouts match Python, including reference choices, batched reveal, and par")
print("PASS: Explore or Exploit controller matches Python batched coins, verdicts, feedback timing, adaptive progression, and restart")
