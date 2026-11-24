"""Check Who Knows What? stories and panel snapshots against Python."""

from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import beliefs
from neural_workshop.ui.taskoptions import who_knows_what_note

KINDS = ("put", "move", "leave", "enter", "call", "lie", "peek")
QUESTIONS = ("truth", "first", "second")


def compare(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    actions, questions = set(), set()
    for rung in range(1, 31):
        for seed in range(-5, 20):
            story = beliefs.deal(rung, seed)
            kind, who, other, thing = story.asked
            questions.add(kind)
            expected = (rung, seed, len(story.people), len(story.containers), len(story.things),
                        len(story.events), QUESTIONS.index(kind), who, other, thing, story.answer)
            actual = tuple(map(int, next(rows).split()))
            assert actual == expected, (rung, seed, actual, expected)
            assert next(rows) == story.question
            assert next(rows) == who_knows_what_note({"WHO_KNOWS_WHAT_RUNG": rung})
            assert tuple(beliefs.PEOPLE[int(next(rows))] for _ in story.people) == story.people
            tracker = beliefs.Tracker(len(story.people), len(story.things))
            for i, (e, present, places) in enumerate(zip(story.events, story.present, story.places)):
                actions.add(e.kind)
                mask = sum(1 << who for who in present)
                contents = dict(places)
                expected = (KINDS.index(e.kind), e.who, e.other, e.thing, e.where,
                            mask, *(contents.get(thing, -1) for thing in range(3)))
                actual = tuple(map(int, next(rows).split()))
                assert actual == expected, (rung, seed, i, actual, expected)
                assert next(rows) == beliefs.caption(story, i)
                tracker.apply(e)
                beliefs_at_event = []
                for who, first_order in enumerate(tracker.belief):
                    beliefs_at_event.extend(first_order.get(thing, -1) for thing in range(len(story.things)))
                    for second_order in tracker.second[who]:
                        beliefs_at_event.extend(second_order.get(thing, -1) for thing in range(len(story.things)))
                actual = list(map(int, next(rows).split()))
                assert actual == beliefs_at_event, (rung, seed, i, actual, beliefs_at_event)
    assert actions == set(KINDS) and questions == set(QUESTIONS)
    rng = Random(17)
    first = beliefs.deal(2, rng=rng)
    second = beliefs.deal(3, rng=rng)
    clock_rng = Random(17)
    beliefs.deal(21, rng=clock_rng)
    after_flag = beliefs.deal(21, rng=clock_rng)
    expected_states = (
        (1, 1, 2, 1, -1, 0, 0, 0, 0, -1, 0.0),
        (0, 1, 2, 1, -1, 0, 0, 0, 0, -1, 0.0),
        (1, 2, 3, 1, first.answer, 1, 2, 1, 0, 2600, 0.0),
        (0, 2, 3, 1, first.answer, 1, 2, 1, 0, 2600, 0.0),
        (1, 1, 3, 2, -1, 1, 2, 1, 0, -1, 0.0),
        (1, 2, 2, 2, second.answer, 1, 2, 2, 0, 5200, 0.0),
        (1, 3, 2, 2, -1, 1, 2, 2, 0, -1, 0.0),
        (1, 1, 2, 1, -1, 0, 0, 0, 0, -1, 0.0),
        (1, 1, 21, 1, -1, 0, 0, 0, 0, -1, 0.5),
        (1, 4, 21, 1, -1, 0, 0, 0, 1, -1, 0.0),
        (1, 1, 21, 2, -1, 0, 0, 0, 1, -1, 0.25),
        (1, 2, 22, 2, after_flag.answer, 1, 21, 1, 1, 2600, 0.25),
        (1, 2, 22, 2, after_flag.answer, 1, 21, 1, 1, 2600, 0.25),
        (1, 3, 22, 2, -1, 1, 21, 1, 1, -1, 0.25),
    )
    for expected in expected_states:
        *fields, bank = next(rows).split()
        actual = (*map(int, fields), float(bank))
        assert actual == expected, (actual, expected)
    assert next(rows, None) is None
    print("PASS: 750 Who Knows What? stories with exact beliefs, captions, panel snapshots, and two controller replays")


if __name__ == "__main__":
    compare(sys.argv[1])
