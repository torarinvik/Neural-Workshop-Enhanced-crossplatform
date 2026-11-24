"""Compare Ferry's display list with the original river and dock animation."""
from functools import lru_cache
from random import Random
import subprocess
import sys
from types import SimpleNamespace

from kitchen_scene_diff import capture, compare_arcs
from sokobanlive_scene_diff import decode
from sonar_scene_diff import compare_commands, state
from neural_workshop import ferry as model
from neural_workshop.ui import ferry, taskoptions


@lru_cache(maxsize=None)
def fixture_yard(rung, seed):
    return model.deal(rung, seed=seed)


class Screen(ferry.Ferry):
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
        self.keys = {symbol: False for symbol in (ferry.key.LEFT, ferry.key.RIGHT, ferry.key.UP,
                                                   ferry.key.DOWN, ferry.key.A, ferry.key.D,
                                                   ferry.key.W, ferry.key.S)}
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
        screen.keys[ferry.key.UP] = True
        for k in range(1, 15):
            screen.keys[ferry.key.RIGHT] = k < 6
            screen.now = k * 0.125
            screen.update(0)
        screen.keys[ferry.key.UP] = False
    run = screen.run
    if mode == 3 and run.level.lanes:
        x, y, _ = run.barge_positions()[0]
        run.x, run.y = x + 10.0, y
    if mode == 4:
        run.x, run.y = run.target()
        run.speed = 0.0
        run.docked_since = run.t - 1.25
    if mode == 5:
        run.x = model.WORLD_W
        screen.update(0)
    if mode >= 6:
        run.t += 3.0
        run.leg = run.level.crossings
        run.x, run.y = run.target()
        run.speed = 0.0
        run.docked_since = run.t - 2.01
        screen.update(0)
        if mode == 7:
            screen.now = 4.75
            screen.update(0)
    return screen


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    for rung in taskoptions.FERRY.options[0].values:
        assert next(rows) == f"note {rung} {taskoptions.ferry_note({'FERRY_RUNG': rung})}"
    count = 0
    for rung in (1, 7, 16, 30):
        for mode in range(8):
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
    print(f"PASS: {count} Ferry scenes match Python river geometry, fog visibility, docking, and feedback")


if __name__ == "__main__":
    main(sys.argv[1])
