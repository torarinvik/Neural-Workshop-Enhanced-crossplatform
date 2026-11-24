"""Compare Full Stop's rendered page and session stages with Python."""
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from full_stop_diff import fullstop, hand, passages, proofreader, sentences, wordlist
from kitchen_scene_diff import capture
from sokobanlive_scene_diff import decode
from sonar_scene_diff import compare_commands, state
from neural_workshop.ui import fullstop as ui, taskoptions


class Screen(ui.FullStop):
    def __init__(self, rung):
        self.rng = Random(17)
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
        self._reset()

    def _tones_live(self, *_):
        pass

    def _tones_stop(self):
        pass

    def _redraw(self):
        if self.record:
            super()._redraw()


def scenario(rung, mode):
    screen = Screen(rung)
    if mode:
        screen.start_run()
    run = screen.run
    if 2 <= mode <= 4:
        x, y, _ = run.places[0]
        run.hand.to(x, y)
        screen.steer(hand.PRESS)
    if mode in (3, 4):
        screen.steer(hand.RELEASE)
        screen.steer(fullstop.RESET)
        screen.steer(fullstop.DONE_KEY)
        screen.now = 0.1
        screen.update(0.1)
        if mode == 4:
            screen.now = 4.1
            screen.update(0)
    if mode >= 5:
        while run.result is None:
            screen.steer(fullstop.autopilot(run)[0])
            screen.now += 1 / 60
            screen.update(1 / 60)
        if mode == 6:
            screen.now = screen.feedback_until
            screen.update(0)
    return screen


def main(binary):
    state.window = SimpleNamespace(width=912, height=684)
    state.cfg = SimpleNamespace(COLOR_LABEL_CORRECT=(64, 255, 64, 255),
                                COLOR_LABEL_INCORRECT=(255, 64, 64, 255))
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    for rung in taskoptions.STOP.options[0].values:
        assert next(rows) == f"note {rung} {taskoptions.fullstop_note({'STOP_RUNG': rung})}"
    seeds = SimpleNamespace(entries=tuple(entry for entry in wordlist.SEED if len(entry.word) <= 15))
    with patch.object(sentences, "index_ready", return_value=False), patch.object(sentences, "pool", return_value=seeds):
        sentences._RANKS = None
        sentences._VOCAB.clear()
        vocabulary = dict.fromkeys(sentences.vocabulary(sentences.TOP_RANK), 1)
    proofreader.pairs.cache_clear()
    passage_bank = tuple(map(passages.split, passages.SEED))
    sentence_bank = tuple(sentences.Sentence(tuple(line.split()), 0) for line in sentences.SEED_TEXT)
    phases = {"ready": 0, "playing": 1, "judged": 2, "done": 3}
    count = 0
    with patch.object(passages, "bank", return_value=passage_bank), patch.object(
        sentences, "bank", return_value=sentence_bank
    ), patch.object(proofreader, "_rank_of", return_value=vocabulary):
        for rung in (1, 10, 30):
            for mode in range(7):
                for dark in range(2):
                    screen = scenario(rung, mode)
                    score = screen.score()
                    where = rung, mode, dark
                    stage = (*where, phases[screen.phase], screen.rung, screen.trial, score["passed"], score["best_rung"])
                    assert next(rows) == "frame " + " ".join(map(str, stage)), stage
                    expected, labels = capture(screen, dark)
                    actual, actual_labels = decode(rows, polygon_colours={colour for kind, colour in expected if kind == "polygon"})
                    assert actual.keys() == expected.keys(), (where, actual.keys() - expected.keys(), expected.keys() - actual.keys())
                    for key in expected:
                        compare_commands(actual[key], expected[key], (where, key))
                    # Kitchen's shared label recorder lacks a live content_width.
                    labels = [(colour, x, y, min(size, size * 912 * 0.96 / (len(text) * int(size * 0.8 + 0.5)))
                               if y == 614 else size, text) for colour, x, y, size, text in labels]
                    compare_commands(actual_labels, labels, where)
                    count += 1
    assert next(rows, None) is None
    print(f"PASS: {count} Full Stop frames and nine option descriptions match Python")


if __name__ == "__main__":
    main(sys.argv[1])
