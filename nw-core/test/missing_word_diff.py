"""Compare seeded Missing Word candidates with the Python generator."""
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pyglet

from crane_diff import compare
from neural_workshop import hand, missingword, passages, proofreader, sentences, wordlist


RUNGS = (0, 1, 3, 4, 6, 7, 10, 13, 16, 19, 22, 25, 28, 30, 41, 99)


def verify_machine(lines, machine, draw, where):
    compare(lines, "deal", (int(machine is not None), draw.random()), where)
    if machine is None:
        return 0
    compare(lines, "seed", (machine.seed,), where)
    offers = 0
    for row, (original, damaged) in enumerate(zip(machine.original, machine.rows)):
        assert next(lines).split() == [f"{row * 100 + i}:{word}" for i, word in enumerate(original)], where
        assert next(lines).split() == [f"{token.id}:{token.text}" for token in damaged], where
        for first, second in zip(damaged, damaged[1:]):
            assert next(lines).split() == list(missingword.offer(machine, first, second)), (where, first, second)
            offers += 1
    for kind, row, index in machine.damage:
        assert next(lines) == f"{missingword.KINDS.index(kind)} {row} {index}", where
    return offers


def verify_run(lines, machine, rung, policy):
    if machine is None:
        return 0
    run = missingword.Run(machine)
    if policy == 1:
        run.hand.x = missingword.centres(run.rows[0])[0]
        run.hand.y = 540.0
        for port in (hand.PRESS, hand.PRESS, hand.RELEASE):
            missingword.act(run, port)
        run.hand.x, run.hand.y = missingword.option_x(0, 1), missingword.OPT_Y
        missingword.act(run, hand.PRESS)
        compare(lines, "struck", (len(run.rows[0]),), rung)
        missingword.act(run, missingword.RESET)
        compare(lines, "reset", (len(run.rows[0]),), rung)
        missingword.act(run, missingword.DONE_KEY)
    elif policy == 2:
        run.step(machine.seconds)
    ticks = 0
    while run.result is None:
        port = missingword.autopilot(run)[0]
        missingword.act(run, port)
        run.step(1 / 60)
        choice = (0, 0, 0) if run.chosen is None else (
            1 if run.chosen[0] == "word" else 2, *run.chosen[1:])
        result = 0 if run.result is None else 1
        compare(lines, "tick", (port, run.t, run.hand.x, run.hand.y, int(run.hand.down), *choice, result),
                (rung, ticks))
        ticks += 1
    assert run.result[0] == (policy == 0)
    compare(lines, "result", ((1, 2, 3)[policy], run.t, run.made), (rung, policy))
    for cue in run.notes:
        compare(lines, "cue", (cue.t, cue.dur, cue.freq, cue.voice, cue.gain), (rung, policy))
    return ticks


def verify_page(lines, machine, rung, mode):
    if machine is None:
        return 0
    from neural_workshop.ui.missingword import MissingWord

    scale = 389 / 640
    left = (912 - 1000 * scale) / 2
    bottom = 179
    where = (rung, mode, "page")

    def rgba(color):
        if len(color) == 3:
            color = (*color, 255)
        return int.from_bytes(bytes(color), "big")

    class Page(MissingWord):
        def __init__(self):
            pass

        def g(self):
            return None

        def rect(self, x, y, width, height, color, group):
            compare(lines, "draw", (1, rgba(color), left + x * scale, bottom + y * scale,
                                    width * scale, height * scale, 0.0), where, tolerance=0.00005)

        def line(self, start, end, width, color, group):
            compare(lines, "draw", (6, rgba(color), left + start[0] * scale, bottom + start[1] * scale,
                                    left + end[0] * scale, bottom + end[1] * scale, width * scale), where, tolerance=0.00005)

        def words(self, label, x, y, size, **kwargs):
            tag, color, actual_x, actual_y, actual_size, text = next(lines).split(" ", 5)
            assert tag == "text" and text == label, (where, label, text)
            compare(iter([f"text {color} {actual_x} {actual_y} {actual_size}"]), "text",
                    (rgba(kwargs["colour"]), left + x * scale, bottom + y * scale, size * scale), where, tolerance=0.00005)

        def poly(self, points, color, group):
            for i, (x, y) in enumerate(points):
                compare(lines, "draw", (8 if i == 0 else 9, rgba(color) if i == 0 else 0,
                                        left + x * scale, bottom + y * scale, 0.0, 0.0, 0.0), where, tolerance=0.00005)

    run = missingword.Run(machine)
    if mode == 1:
        run.hand.to(missingword.centres(run.rows[0])[0], 540.0)
        missingword.act(run, hand.PRESS)
    elif mode == 2:
        run.hand.to(missingword.carets(run.rows[0])[0], 510.0)
        missingword.act(run, hand.PRESS)
    Page()._scene(run, scale)
    assert next(lines) == "end", where
    return 1


def verify_candidates(binary, stdin):
    lines = iter(subprocess.check_output([binary], input=stdin, text=True).splitlines())
    from neural_workshop.ui import taskoptions

    for rung in taskoptions.GAPW.options[0].values:
        assert next(lines) == f"note {rung} {taskoptions.missingword_note({'GAPW_RUNG': rung})}"
    accepted = offers = ticks = pages = 0
    accepted_lengths = set()
    for rung in RUNGS:
        grade = missingword.grade(rung)
        compare(lines, "level", (grade.rung, grade.sentences, len(grade.kinds), grade.errors,
                                 int(grade.hint), int(grade.close), grade.seconds), rung)
        for seed in range(24):
            draw = Random(seed)
            machine = missingword.build(grade, draw)
            offers += verify_machine(lines, machine, draw, (rung, seed))
            if machine is not None:
                accepted += 1
                accepted_lengths.add(grade.sentences)
        draw = Random(17)
        try:
            machine = missingword.deal(rung, rng=draw)
        except RuntimeError:
            machine = None
        offers += verify_machine(lines, machine, draw, (rung, "screened"))
        ticks += verify_run(lines, machine, rung, 0)
        if rung == 1:
            verify_run(lines, machine, rung, 1)
            verify_run(lines, machine, rung, 2)
        for mode in range(3):
            pages += verify_page(lines, machine, rung, mode)
    assert next(lines, None) is None
    assert ticks
    return accepted, accepted_lengths, offers, ticks, pages


def clear_caches():
    sentences.forget()
    passages.forget()
    proofreader.pairs.cache_clear()
    proofreader.families.cache_clear()
    proofreader._rank_of.cache_clear()
    proofreader._ranked.cache_clear()
    missingword._tokens.cache_clear()


def main(binary):
    pyglet.options.shadow_window = False
    seed_pool = SimpleNamespace(entries=tuple(entry for entry in wordlist.SEED if len(entry.word) <= 15))
    clear_caches()
    with patch.object(sentences, "index_ready", return_value=False), patch.object(
        sentences, "pool", return_value=seed_pool
    ), patch.object(sentences, "have", return_value=False), patch.object(passages, "have", return_value=False):
        offline, offline_lengths, offline_offers, offline_ticks, offline_pages = verify_candidates(binary, "")
        ranks = sentences.ranks().copy()
    assert {1, 3} <= offline_lengths
    # Generate passages of every supported length. Explicit ranked and unranked
    # words test source filtering and first-word normalization independently.
    ranks["clara"] = 60000
    ranks["house"] = 60001
    tails = ("Clara walked to the river late.", "It was quiet in the garden.")
    passage_lines = list(passages.SEED)
    for count in range(2, 7):
        for start in range(18):
            original = tuple(" ".join(words) + "." for words in passages.split(passages.SEED[start]))
            candidates = original + tails + original
            passage_lines.append(" ".join(candidates[:count]))
    sentence_lines = list(sentences.SEED_TEXT) * 2 + ["clara went to the little house"]
    vocabulary = [f"{word}\t{rank}\tDefinition" for word, rank in reversed(tuple(ranks.items()))]
    # The Python word pool excludes entries longer than fifteen letters.
    vocabulary.append("counterclockwise\t1\tDefinition")
    payload = "\1" + "\0".join("\n".join(lines) for lines in (passage_lines, sentence_lines, vocabulary))
    assert all(len("\n".join(lines)) > 4096 for lines in (passage_lines, sentence_lines))
    clear_caches()
    with patch.object(sentences, "ranks", return_value=ranks), patch.object(
        sentences, "bank", return_value=sentences._graded(sentence_lines)
    ), patch.object(passages, "bank", return_value=tuple(map(passages.split, passage_lines))):
        custom, custom_lengths, custom_offers, custom_ticks, custom_pages = verify_candidates(binary, payload)
    assert custom_lengths == set(range(1, 7))
    total = 2 * len(RUNGS) * 24
    print(f"PASS: {total} Missing Word candidates ({offline + custom} accepted) and {offline_offers + custom_offers:,} gap offers match Python")
    print(f"PASS: 32 screened deals and {offline_ticks + custom_ticks:,} reference-player ticks match Python")
    print(f"PASS: {offline_pages + custom_pages} Missing Word pages and nine option descriptions match Python")


if __name__ == "__main__":
    main(sys.argv[1])
