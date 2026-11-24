"""Compare Unicycle's side-scrolling track and rider with Python."""
from functools import lru_cache
from random import Random
import subprocess
import sys
from types import SimpleNamespace

from kitchen_scene_diff import capture
from sokobanlive_scene_diff import decode
from sonar_scene_diff import compare_commands, state
from neural_workshop import unicycle as model
from neural_workshop.ui import unicycle, taskoptions


@lru_cache(maxsize=None)
def track(rung):
    return model.deal(rung, rng=Random(17))


class Screen(unicycle.Unicycle):
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
        self.keys = dict.fromkeys((unicycle.key.W, unicycle.key.S, unicycle.key.A, unicycle.key.D,
                                   unicycle.key.UP, unicycle.key.DOWN, unicycle.key.LEFT, unicycle.key.RIGHT), False)
        self._reset()

    def _make_run(self):
        return model.Run(track(self.rung))

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
        for key in (unicycle.key.UP, unicycle.key.W, unicycle.key.LEFT):
            screen.keys[key] = True
        for frame in range(1, 14):
            if frame == 3:
                screen.keys[unicycle.key.UP] = False
            if frame == 7:
                screen.keys[unicycle.key.RIGHT] = True
            if frame == 9:
                screen.keys = dict.fromkeys(screen.keys, False)
            screen.now = 0.025 * frame
            screen.update(0)
    if mode in (3, 4):
        x = run.tr.finish - 2
        y = model.ground(run.tr, x)
        run.body = run.body._replace(px=x, py=y + 0.35, qx=x + 0.15, qy=y + 1.3, a=0.9)
        run.t = 5.0
        if mode == 4:
            run.result = (True, "At the flag in 5.0 s")
            screen._judge(*run.result)
    if mode in (5, 6, 8):
        run.body = run.body._replace(qy=0.1) if mode != 6 else run.body._replace(py=-0.4, qy=0.08)
        screen.update(0)
        if mode == 8:
            screen.now = 2.5
            screen.update(0)
    if mode == 7:
        run.t = run.tr.seconds + 0.1
        screen.update(0)
    return screen


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    for rung in taskoptions.UNI.options[0].values:
        assert next(rows) == f"note {rung} {taskoptions.unicycle_note({'UNI_RUNG': rung})}"
    count = 0
    for rung in (1, 4, 13, 30):
        for mode in range(9):
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
    print(f"PASS: {count} Unicycle track, rider, and feedback scenes matched Python")


if __name__ == "__main__":
    main(sys.argv[1])
