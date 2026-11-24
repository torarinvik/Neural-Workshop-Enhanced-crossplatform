"""Replay original Full Stop generation, wrapping, pointer moves, and scoring."""
from random import Random
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

from crane_diff import compare
from neural_workshop import fullstop, hand, passages, proofreader, sentences, wordlist


RUNGS = (1, 4, 9, 10, 13, 14, 19, 20, 22, 23, 30, 41, 99)


def check_machine(rows, candidate, draw, where):
    compare(rows, "deal", (int(candidate is not None), draw.random()), where)
    if candidate is None:
        return False
    compare(rows, "size", (len(candidate.words), candidate.seconds), where)
    for i, word in enumerate(candidate.words):
        assert next(rows) == f"{word} {int(i in candidate.stops)}", (where, i, word)
    return True


def check_run(rows, machine, policy, where):
    run = fullstop.Run(machine)
    compare(rows, "scale", (run.scale,), where)
    for tile in run.places:
        compare(rows, "tile", tile, where)
    if policy == 1:
        x, y, _ = run.places[0]
        run.hand.to(x, y)
        for port in (hand.PRESS, hand.PRESS, hand.RELEASE, hand.PRESS, hand.RELEASE, fullstop.RESET):
            fullstop.act(run, port)
        for (tx, ty, _), ports in (
            (run.places[-1], (hand.PRESS, hand.RELEASE)),
            (run.places[0], (hand.PRESS, fullstop.DONE_KEY)),
        ):
            run.hand.to(tx, ty)
            for port in ports:
                fullstop.act(run, port)
    elif policy == 2:
        run.step(machine.seconds)
    ticks = 0
    while run.result is None:
        port = fullstop.autopilot(run)[0]
        fullstop.act(run, port)
        run.step(1 / 60)
        compare(rows, "tick", (port, run.t, run.hand.x, run.hand.y, int(run.hand.down),
                               len(run.stops), 0 if run.result is None else 1), (*where, ticks))
        ticks += 1
    result = (1, 2, 3)[policy]
    assert run.result[0] == (result == 1)
    compare(rows, "result", (result, len(machine.stops) if policy == 1 else 0, int(policy == 1)), where)
    for cue in run.notes:
        compare(rows, "cue", (cue.t, cue.dur, cue.freq, cue.voice, cue.gain, cue.pan), where)
    return ticks


def replay(binary, passage_lines, sentence_lines, vocabulary, *, bundled=False):
    passage_bank = tuple(passages.split(line) for line in passage_lines)
    sentence_bank = tuple(sentences.Sentence(tuple(line.split()), 0) for line in sentence_lines)
    # The downloaded files must pass the original cache size check.
    lexicon_lines = [f"{word}\t{rank}\tDefinition" for rank, word in enumerate(vocabulary, 1)]
    extras = ("farmer\t60001\tA different rank", "clara\t60000\tA name")
    if not bundled:
        lexicon_lines = [line for line in lexicon_lines if not line.startswith("farmer\t")] + list(extras)
        vocabulary = tuple(word for word in vocabulary if word != "farmer") + ("clara",)
    stdin = "" if bundled else "\1" + "\0".join("\n".join(lines) for lines in (passage_lines, sentence_lines, lexicon_lines))
    rows = iter(subprocess.check_output([binary], input=stdin, text=True).splitlines())
    candidates = accepted = ticks = 0
    proofreader.pairs.cache_clear()
    with patch.object(passages, "bank", return_value=passage_bank), patch.object(
        sentences, "bank", return_value=sentence_bank
    ), patch.object(proofreader, "_rank_of", return_value=dict.fromkeys(vocabulary, 1)):
        for rung in RUNGS:
            level = fullstop.grade(rung)
            compare(rows, "level", (rung, level.sentences, int(level.hint), int(level.flat), int(level.short),
                                    level.pace), rung)
            for seed in range(32):
                draw = Random(seed)
                candidate = fullstop.build(level, draw)
                accepted += check_machine(rows, candidate, draw, (rung, seed))
                candidates += 1
            draw = Random(17)
            try:
                candidate = fullstop.deal(rung, rng=draw)
            except RuntimeError:
                candidate = None
            if check_machine(rows, candidate, draw, (rung, "screened")):
                ticks += check_run(rows, candidate, 0, (rung, "screened"))
                if rung == 1:
                    for policy in (1, 2):
                        check_run(rows, candidate, policy, (rung, policy))
    assert next(rows, None) is None
    assert 0 < accepted < candidates and ticks > 0
    return candidates, accepted, ticks


def main(binary):
    seed_pool = SimpleNamespace(entries=tuple(entry for entry in wordlist.SEED if len(entry.word) <= 15))
    with patch.object(sentences, "index_ready", return_value=False), patch.object(sentences, "pool", return_value=seed_pool):
        sentences._RANKS = None
        sentences._VOCAB.clear()
        vocabulary = tuple(sentences.vocabulary(sentences.TOP_RANK))
    offline = replay(binary, passages.SEED, sentences.SEED_TEXT, vocabulary, bundled=True)
    custom = replay(binary, passages.SEED * 2 + (
        "Ada found a stray bird. She put it inside her coat. It flew away at sunset.",
        "The quiet child knew Clara. Clara wrote about the marsh. Clara planned another walk.",
        "Alice walked home before dinner. Farmer was still outside alone. NASA sent its team.",
    ), sentences.SEED_TEXT * 2 + ("the bird she liked was blue", "sunset the farmers went home"), vocabulary)
    total, accepted, ticks = (sum(pair) for pair in zip(offline, custom))
    print(f"PASS: {total} Full Stop candidates ({accepted} accepted) and {ticks:,} replay ticks match Python")


if __name__ == "__main__":
    main(sys.argv[1])
