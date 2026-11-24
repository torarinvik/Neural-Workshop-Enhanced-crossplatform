"""Compare Proofreader candidates and their RNG state against Python."""
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from crane_diff import compare
from missing_word_diff import clear_caches
import pyglet

from neural_workshop import hand, passages, proofreader, sentences, wordlist


RUNGS = (0, 1, 2, 4, 7, 10, 13, 16, 19, 22, 25, 28, 30, 41, 99)


def verify_machine(lines, machine, draw, where):
    compare(lines, "deal", (int(machine is not None), draw.random()), where)
    if machine is None:
        return 0
    offers = 0
    for row, (original, damaged) in enumerate(zip(machine.original, machine.rows)):
        expected = [f"{row * 100 + i}:{word}" for i, word in enumerate(original)]
        assert next(lines).split() == expected, (where, row, "original")
        expected = [f"{token.id}:{token.text}" for token in damaged]
        assert next(lines).split() == expected, (where, row, "damaged")
        assert int(next(lines)) == machine.row_of[row], where
        for token in damaged:
            expected = list(machine.options.get(token.id, ()))
            assert next(lines).split() == expected, (where, token, expected)
            offers += bool(expected)
    for kind, row, index in machine.damage:
        assert next(lines) == f"{proofreader.KINDS.index(kind)} {row} {index}", where
    return offers


def verify_replay(lines, machine, rung, policy):
    if machine is None:
        return 0
    run = proofreader.Run(machine)
    if policy == 1:
        proofreader.act(run, proofreader.RESET)
        proofreader.act(run, proofreader.DONE_KEY)
    elif policy == 2:
        run.step(machine.seconds)
    ticks = 0
    while run.result is None:
        port = proofreader.autopilot(run)[0]
        proofreader.act(run, port)
        run.step(1 / 60)
        carry = (0, 0, 0) if run.carry is None else (
            (1, run.carry[1], 0) if run.carry[0] == "row" else (2, *run.carry[1:]))
        selected = -1 if run.selected is None else run.selected
        compare(lines, "tick", (port, run.t, run.hand.x, run.hand.y, int(run.hand.down),
                                *carry, selected, run.moves), (rung, ticks))
        ticks += 1
    assert run.result[0] == (policy == 0), (rung, policy, run.result)
    compare(lines, "result", (policy + 1, run.t, run.moves), (rung, policy))
    for cue in run.notes:
        compare(lines, "cue", (cue.t, cue.dur, cue.freq, cue.voice, cue.gain, cue.pan), (rung, policy))
    return ticks


def verify_page(lines, machine, rung, mode):
    if machine is None:
        return 0
    from neural_workshop.ui.proofreader import Proofreader

    scale = 389 / 640
    left = (912 - 1000 * scale) / 2
    bottom = 179
    where = (rung, mode, "page")

    def rgba(color):
        if len(color) == 3:
            color = (*color, 255)
        return int.from_bytes(bytes(color), "big")

    class Page(Proofreader):
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

    run = proofreader.Run(machine)
    if mode == 1:
        run.hand.to(proofreader.HANDLE_X, 540.0)
        proofreader.act(run, hand.PRESS)
        run.hand.to(proofreader.HANDLE_X, 520.0)
    elif mode >= 2:
        run.hand.to(proofreader.centres(run.rows[0])[0], 540.0)
        proofreader.act(run, hand.PRESS)
        if mode == 2:
            run.hand.to(500.0, 520.0)
        else:
            proofreader.act(run, hand.RELEASE)
    Page()._scene(run, scale)
    assert next(lines) == "end", where
    return 1


def verify(binary, payload):
    lines = iter(subprocess.check_output([binary], input=payload, text=True).splitlines())
    from neural_workshop.ui import taskoptions

    for rung in taskoptions.PROOF.options[0].values:
        assert next(lines) == f"note {rung} {taskoptions.proofreader_note({'PROOF_RUNG': rung})}"
    accepted = offers = ticks = pages = 0
    kinds = set()
    lengths = set()
    for rung in RUNGS:
        grade = proofreader.grade(rung)
        compare(lines, "level", (grade.rung, grade.sentences, len(grade.kinds), grade.errors,
                                 int(grade.hint), int(grade.whole), int(grade.close), grade.seconds), rung)
        for seed in range(24):
            draw = Random(seed)
            machine = proofreader.build(grade, draw)
            offers += verify_machine(lines, machine, draw, (rung, seed))
            if machine is not None:
                accepted += 1
                lengths.add(grade.sentences)
                kinds.update(kind for kind, *_ in machine.damage)
        draw = Random(17)
        try:
            screened = proofreader.deal(rung, rng=draw)
        except RuntimeError:
            screened = None
        verify_machine(lines, screened, draw, (rung, "screened"))
        ticks += verify_replay(lines, screened, rung, 0)
        if rung == 1:
            verify_replay(lines, screened, rung, 1)
            verify_replay(lines, screened, rung, 2)
        for mode in range(4):
            pages += verify_page(lines, screened, rung, mode)
    assert next(lines, None) is None
    return accepted, offers, kinds, lengths, ticks, pages


def main(binary):
    pyglet.options.shadow_window = False
    seed_pool = SimpleNamespace(entries=tuple(entry for entry in wordlist.SEED if len(entry.word) <= 15))
    clear_caches()
    with patch.object(sentences, "index_ready", return_value=False), patch.object(
        sentences, "pool", return_value=seed_pool
    ), patch.object(sentences, "have", return_value=False), patch.object(passages, "have", return_value=False):
        offline = verify(binary, "")
        ranks = sentences.ranks().copy()
    passage_lines = list(passages.SEED)
    for length in (2, 4, 5, 7):
        for source in passages.SEED[:18]:
            original = passages.split(source)
            variants = original + passages.split("Clara walked to the river late. It was quiet in the garden.") + original
            passage_lines.append(" ".join(" ".join(row) + "." for row in variants[:length]))
    sentence_lines = list(sentences.SEED_TEXT) * 2
    vocabulary_lines = [f"{word}\t{rank}\tDefinition" for word, rank in reversed(tuple(ranks.items()))]
    payload = "\1" + "\0".join("\n".join(lines) for lines in (passage_lines, sentence_lines, vocabulary_lines))
    assert all(len("\n".join(lines)) > 4096 for lines in (passage_lines, sentence_lines))
    clear_caches()
    with patch.object(sentences, "ranks", return_value=ranks), patch.object(
        sentences, "bank", return_value=sentences._graded(sentence_lines)
    ), patch.object(passages, "bank", return_value=tuple(map(passages.split, passage_lines))):
        custom = verify(binary, payload)
    assert custom[2] == set(proofreader.KINDS)
    assert custom[3] == set(range(1, 7))
    print(f"PASS: {2 * len(RUNGS) * 24} Proofreader candidates, {offline[0] + custom[0]} accepted, "
          f"and {offline[1] + custom[1]:,} word offers match Python")

    print(f"PASS: 30 screened deals and {offline[4] + custom[4]:,} editor replay ticks match Python")

    print(f"PASS: {offline[5] + custom[5]} normal and interactive Proofreader pages and nine option notes match Python")


if __name__ == "__main__":
    main(sys.argv[1])
