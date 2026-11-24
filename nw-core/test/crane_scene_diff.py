"""Compare Crane's display list with the original harbor and moving objects."""
from functools import lru_cache
from random import Random
import subprocess
import sys
from types import SimpleNamespace

from kitchen_scene_diff import capture, compare_arcs
from sokobanlive_scene_diff import decode
from sonar_scene_diff import compare_commands, state
from neural_workshop import crane as model
from neural_workshop.ui import crane, taskoptions


@lru_cache(maxsize=None)
def fixture_yard(rung, seed):
    return model.deal(rung, seed=seed)


class Screen(crane.Crane):
    def __init__(self, rung):
        self.rng = Random(17)
        self.start_rung = self.rung = rung
        self.total_trials = 1
        self.adaptive = True
        self.now = 0.0
        self.clock = lambda: self.now
        self.drawn, self.scenery = [], []
        self.scenery_key = None
        self.verdict = SimpleNamespace(clear=lambda: None, show=lambda *_: None)
        self.record = False
        self.keys = {symbol: False for symbol in (crane.key.LEFT, crane.key.RIGHT, crane.key.UP,
                                                   crane.key.DOWN, crane.key.A, crane.key.D,
                                                   crane.key.W, crane.key.S)}
        self._reset()

    def _make_run(self):
        return model.Run(fixture_yard(self.rung, self.rng.randrange(1 << 30)))

    def _redraw(self):
        if self.record:
            super()._redraw()


def scenario(rung, mode):
    screen = Screen(rung)
    if mode:
        screen.start_run()
    if mode >= 2:
        screen.keys[crane.key.RIGHT] = True
        for k in range(1, 13):
            screen.now = k * 0.125
            screen.update(0)
        screen.keys[crane.key.RIGHT] = False
    if mode >= 3:
        run = screen.run
        item, bay = model._next_job(run)
        run.x, bottom = run.box_rect(item)
        run.v = run.theta = run.omega = 0.0
        run.cable = model.RAIL - (bottom + model.BOX_H)
        if mode >= 4:
            run.grab()
            run.theta, run.omega, run.cable = 0.08, -0.15, 6.0
        if mode >= 5:
            run.x = run.yard.bays[bay].x
            run.theta = run.omega = 0.0
            run.cable = model.RAIL - (model.BOX_H + (3.0 if mode == 5 else 0.0))
            run.grab()
            if mode == 6:
                run.placed = len(run.yard.boxes)
            if mode != 7:
                screen.update(0)
            if mode == 8:
                screen.now = 4.5
                screen.update(0)
    return screen


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    for rung in taskoptions.CRANE.options[0].values:
        assert next(rows) == f"note {rung} {taskoptions.crane_note({'CRANE_RUNG': rung})}"
    count = 0
    for rung in (1, 13, 20, 30):
        for mode in range(9):
            for dark in range(2):
                where = rung, mode, dark
                assert next(rows) == f"frame {rung} {mode} {dark}"
                expected, labels = capture(scenario(rung, mode), dark)
                actual, actual_labels = decode(rows)
                compare_arcs(actual, expected, where)
                assert actual.keys() == expected.keys(), (where, actual.keys() - expected.keys(), expected.keys() - actual.keys())
                for key, commands in expected.items():
                    compare_commands(actual[key], commands, (where, key))
                compare_commands(actual_labels, labels, where)
                count += 1
    assert next(rows, None) is None
    print(f"PASS: {count} Crane scenes match Python harbor geometry, controls, and feedback")


if __name__ == "__main__":
    main(sys.argv[1])
