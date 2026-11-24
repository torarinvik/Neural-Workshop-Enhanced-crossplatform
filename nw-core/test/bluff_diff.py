"""Compare Bluff deals, hand histories, rewards, and adaptive opponent notes."""
from pathlib import Path
from random import Random
import subprocess
import sys
from types import SimpleNamespace

import pyglet

pyglet.options.shadow_window = False

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import bluff
from neural_workshop.ui.bluff import Bluff


RUNGS = (0, 1, 2, 3, 5, 7, 9, 10, 13, 14, 17, 18, 20, 21, 30)
KINDS = (bluff.STATION, bluff.ROCK, bluff.MANIAC, bluff.SOUND, bluff.ADAPTIVE)
SPOTS = ("", "c", "b", "cb", "cc", "bk", "cbk", "bf", "cbf")


def compare(rows, label, expected, where):
    kind, *fields = next(rows).split()
    assert kind == label and len(fields) == len(expected), (where, kind, fields, label, expected)
    for index, (field, value) in enumerate(zip(fields, expected)):
        parsed = float(field) if isinstance(value, float) else int(field)
        assert parsed == value, (where, label, index, parsed, value)


def replay(rows, dealt, policy, where):
    game = bluff.Match(dealt)
    model = bluff.Model(dealt.level.cards)
    move_count = 0
    settled = set()
    while not game.over:
        index = game.index
        if policy == 0:
            choice = 0
        elif policy == 1:
            choice = move_count % 2
        elif policy == 2:
            choice = int(game.hand.player * 2 >= dealt.level.cards - 1)
        elif policy == 3:
            choice = bluff.reference_move(model, game)
        else:
            sound = bluff.Habits(bluff.SOUND)
            strength = bluff.strength(game.hand.player, dealt.level.cards)
            choice = int((game.hand.coins[0] + 0.5) % 1.0 < sound.aggression(strength, game.spot))
        compare(rows, "move", (index, SPOTS.index(game.spot), choice), where)
        assert game.act(choice)
        move_count += 1
        if game.index > index:
            record = game.records[index]
            settled.add(record.actions)
            if policy == 3:
                model.saw(record)
            compare(rows, "record", (SPOTS.index(record.actions), record.player_card,
                                      -1 if record.shown is None else record.shown,
                                      record.won, game.worths[index]), where)
    compare(rows, "score", (game.chips, game.value), where)
    for index, kind in enumerate(KINDS):
        habit = game.habits.get(kind) or bluff.Habits(kind)
        compare(rows, "habit", (index, habit.bets, habit.bluffs, habit.shown, habit.folds, habit.faced), where)
    return settled


class Screen(Bluff):
    def __init__(self):
        self.rng = Random(-17)
        self.start_rung = 18
        self.total_trials = 2
        self.adaptive = True
        self.now = 0
        self.clock = lambda: self.now / 1000
        self.verdict = SimpleNamespace(show=lambda *_: None, clear=lambda: None)

    def _redraw(self):
        pass


def controller(rows):
    screen = Screen()
    screen.start_run()
    for trial in range(2):
        compare(rows, "trial", (screen.rung, screen.trial, screen.par), trial)
        model = bluff.Model(screen.match.level.cards)
        while screen.phase == "playing":
            index = screen.match.index
            choice = bluff.reference_move(model, screen.match) if trial == 0 else 0
            screen.now += 16
            screen.act(choice)
            if screen.match.index > index:
                model.saw(screen.match.records[index])
        assert screen.phase == "judged"
        assert screen.verdict_shown[0] == (trial == 0)
        first, later = screen.match.deal.kinds[0][1], screen.match.deal.kinds[-1][1]
        compare(rows, "judged", (screen.rung, screen.score()["passed"], screen.match.value,
                                  screen.match.chips, KINDS.index(first), KINDS.index(later)), trial)
        compare(rows, "early", (0,), trial)
        screen.now += 2999
        screen.update(0)
        assert screen.phase == "judged"
        screen.now += 1
        screen.clock = lambda: screen.feedback_until
        screen.update(0)
        screen.clock = lambda: screen.now / 1000
    assert screen.phase == "done"
    score = screen.score()
    compare(rows, "done", (3, score["passed"], score["best_rung"], 0), "done")
    screen.start_run()
    compare(rows, "restart", (screen.rung, screen.trial, screen.score()["passed"]), "restart")

def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    hands = 0
    settled = set()
    for seed in range(17, 17 + 421 * 4, 421):
        rng = Random(seed)
        for rung in RUNGS:
            dealt = bluff.deal(rung, rng=rng)
            level = dealt.level
            switch, later = dealt.kinds[-1]
            compare(rows, "round", (level.rung, level.cards, level.hands, level.allow, len(level.kinds),
                                     KINDS.index(dealt.kinds[0][1]), KINDS.index(later),
                                     switch if level.changes else level.hands), (seed, rung))
            for kind in level.kinds:
                compare(rows, "kind", (KINDS.index(kind),), (seed, rung))
            for hand in dealt.hands:
                compare(rows, "hand", (hand.player, hand.opponent, hand.player_first, *hand.coins), (seed, rung))
            hands += len(dealt.hands)
            for policy in range(5):
                settled.update(replay(rows, dealt, policy, (seed, rung, policy)))
            compare(rows, "par", (bluff.par(dealt),), (seed, rung))
    controller(rows)
    assert next(rows, None) is None
    assert settled == set(SPOTS[4:]), settled
    print(f"PASS: {4 * len(RUNGS)} Bluff deals and {hands} hands matched Python, with {hands * 5} played outcomes")
    print("PASS: Bluff reference and sound choices, par, adaptive feedback, and restart matched Python")


if __name__ == "__main__":
    main(sys.argv[1])
