"""Compare Rover's delayed chase view and command tray with Python."""
from functools import lru_cache
from random import Random
import subprocess
import sys
from types import SimpleNamespace

from kitchen_scene_diff import capture
from sokobanlive_scene_diff import decode
from sonar_scene_diff import compare_commands, state
from neural_workshop import rover as model
from neural_workshop.ui import rover, taskoptions


@lru_cache(maxsize=None)
def ground(rung):
    return model.deal(rung, rng=Random(17))


class Screen(rover.Rover):
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
        self.keys = dict.fromkeys((rover.key.W, rover.key.S, rover.key.A, rover.key.D,
                                   rover.key.UP, rover.key.DOWN, rover.key.LEFT, rover.key.RIGHT), False)
        self._reset()

    def _make_run(self):
        return model.Run(ground(self.rung))

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
    if mode in (2, 3):
        screen.keys[rover.key.W] = True
        for frame in range(1, 30):
            if frame == 10:
                screen.keys[rover.key.W] = False
                screen.keys[rover.key.D] = True
            if frame == 20 and mode == 3:
                screen.keys[rover.key.S] = True
            screen.now = frame * 0.125
            screen.update(0)
    if mode == 4:
        run.reached = int(run.level.flags > 1)
    if mode in (5, 6, 9):
        message = {5: "Hit a rock", 6: "Tipped over on a slope", 9: f"0 of {run.level.flags} flags"}[mode]
        run.result = (False, message)
        screen._judge(*run.result)
    if mode in (7, 8):
        run.reached = run.level.flags
        run.result = (True, "Every flag in 0 s")
        screen._judge(*run.result)
        if mode == 8:
            screen.now = 2.5
            screen.update(0)
    return screen


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    for rung in taskoptions.ROVER.options[0].values:
        assert next(rows) == f"note {rung} {taskoptions.rover_note({'ROVER_RUNG': rung})}"
    count = 0
    for rung in (1, 4, 13, 30):
        for mode in range(10):
            for dark in range(2):
                where = rung, mode, dark
                assert next(rows) == f"frame {rung} {mode} {dark}"
                expected_order, actual_order = [], []
                expected, labels = capture(scenario(rung, mode), dark, polygons=expected_order)
                colours = {color for kind, color in expected if kind == "polygon"}
                actual, actual_labels = decode(rows, polygon_colours=colours, polygons=actual_order)
                assert actual.keys() == expected.keys(), (where, actual.keys() - expected.keys(), expected.keys() - actual.keys())
                for key, commands in expected.items():
                    compare_commands(actual[key], commands, (where, key))
                compare_commands(actual_labels, labels, where)
                assert len(actual_order) == len(expected_order), where
                for index, (observed, wanted) in enumerate(zip(actual_order, expected_order)):
                    compare_commands([observed], [wanted], (*where, "polygon order", index))
                count += 1
    assert next(rows, None) is None
    print(f"PASS: {count} Rover chase-camera and command-tray scenes matched Python")


if __name__ == "__main__":
    main(sys.argv[1])
