"""Compare the original cockpit with the Elisa display list."""
from functools import lru_cache
from random import Random
import subprocess
import sys
from types import SimpleNamespace

from kitchen_scene_diff import capture
from sokobanlive_scene_diff import decode
from sonar_scene_diff import compare_commands, state
from neural_workshop import docking as model
from neural_workshop.ui import docking, taskoptions


@lru_cache(maxsize=None)
def approach(rung):
    return model.deal(rung, rng=Random(17))


class Screen(docking.Docking):
    def __init__(self, rung):
        self.start_rung = self.rung = rung
        self.total_trials = 1
        self.adaptive = True
        self.now = 0.0
        self.clock = lambda: self.now
        self.run = None
        self.drawn, self.scenery = [], []
        self.scenery_key = None
        self.verdict = SimpleNamespace(clear=lambda: None, show=lambda *_: None)
        self.record = False
        self.keys = dict.fromkeys((docking.key.A, docking.key.D, docking.key.S, docking.key.W,
                                   docking.key.R, docking.key.F, docking.key.LEFT, docking.key.RIGHT,
                                   docking.key.DOWN, docking.key.UP, docking.key.Q, docking.key.E), False)
        self._reset()

    def _make_run(self):
        return model.Run(approach(self.rung))

    def _sound(self):
        pass

    def _redraw(self):
        if self.record:
            super()._redraw()


def scenario(rung, mode):
    screen = Screen(rung)
    if mode:
        screen.start_run()
    run = screen.run
    if mode == 2:
        screen.keys[docking.key.RIGHT] = True
        for k in range(1, 15):
            screen.now = k * 0.125
            screen.update(0)
    if mode == 3:
        run.pos[:] = [0.04, -0.02, -0.55]
        run.att[:] = [0.1, 0.0, 0.2]
        run.fuel = run.ap.fuel * 0.16
    if mode == 4:
        run.pos[:] = [1.0, 0.0, 0.0]
        run.vel[:] = [0.0, 0.0, 2.0]
        run.att[:] = [0.3, 0.0, run.station_roll() + 0.3]
        screen.update(0)
    if mode == 5:
        run.pos[:] = [0.0, 0.0, -100.0]
        screen.update(0)
    if mode >= 6:
        run.pos[:] = [0.0, 0.0, 0.0]
        run.vel[:] = [0.0, 0.0, 0.15]
        run.att[:] = [0.0, 0.0, run.station_roll()]
        screen.update(0)
        if mode == 7:
            screen.now = 2.5
            screen.update(0)
    return screen


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    for rung in taskoptions.BERTH.options[0].values:
        assert next(rows) == f"note {rung} {taskoptions.docking_note({'BERTH_RUNG': rung})}"
    count = 0
    for rung in (1, 7, 16, 30):
        for mode in range(8):
            for dark in range(2):
                where = rung, mode, dark
                assert next(rows) == f"frame {rung} {mode} {dark}"
                expected, labels = capture(scenario(rung, mode), dark)
                actual, actual_labels = decode(rows, polygon_colours=(0x787C88FF, 0x282C38FF))
                assert actual.keys() == expected.keys(), (where, actual.keys() - expected.keys(), expected.keys() - actual.keys())
                for key, commands in expected.items():
                    compare_commands(actual[key], commands, (where, key))
                compare_commands(actual_labels, labels, where)
                count += 1
    assert next(rows, None) is None
    print(f"PASS: {count} Docking cockpit scenes matched Python")


if __name__ == "__main__":
    main(sys.argv[1])
