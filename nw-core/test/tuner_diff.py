"""Replay Tuner deals and radio controls against the original Python model."""
import math
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import soundbank, tuner


def near(values, expected, where):
    assert len(values) == len(expected) and all(
        math.isclose(float(a), b, rel_tol=0, abs_tol=1e-11)
        for a, b in zip(values, expected)
    ), (where, values, expected)


def check_sound(lines, sound, where):
    v = next(lines).split()
    bank = int(sound.bank == "esc50")
    assert tuple(map(int, v[:4])) == (bank, sound.ref[0] if bank else -1, sound.label, sound.group), where
    near(v[4:6], (tuner.length(sound) * sound.speed, sound.speed), where)
    assert int(v[6]) == sound.backward
    if not bank:
        degrees, rhythm, root, voice = sound.ref
        assert int(v[7]) == tuner.RHYTHMS.index(rhythm)
        near(v[8:9], (root,), where)
        assert int(v[9]) == tuner.VOICES.index(voice)
        assert tuple(map(int, v[10:])) == degrees, where


def emit_expected(lines, rung, seed, bank, scenario=0):
    where = (rung, seed, bank, scenario)
    radio = tuner.deal(rung, seed, bank=bank)
    g = radio.level
    v = next(lines).split()
    assert tuple(map(int, v[:8])) == (
        g.rung, len(radio.stations), radio.target, g.lamps, g.same_group, g.shifted, g.fade, g.near_miss
    ), (where, v, radio)
    near(v[8:14], (g.width, g.drift, g.seconds, g.hold, radio.listen, radio.start), where)
    assert int(v[14]) == radio.seed, where
    check_sound(lines, radio.heard, where)
    for station in radio.stations:
        near(next(lines).split(), (station.at, station.phase, *station.sway, *station.fade), where)
        check_sound(lines, station.sound, where)
    run = tuner.Run(radio)
    while run.result is None:
        ports = tuner.autopilot(run) if scenario == 0 else []
        if tuner.LOCK in ports:
            run.press()
        if scenario == 1 and run.on() and len(run.plays) == 1:
            run.replay()
        if scenario == 2 and run.on():
            run.dial = run.where((radio.target + 1) % len(radio.stations))
            run.press()
        run.step(1 / 60.0, ports)
    row = next(lines).split()
    assert int(row[0]) == (1 if run.result[0] else -2 if run.result[1] == "Out of time" else -1), where
    near(row[1:4], (run.t, run.dial, run.replay_until), where)
    assert int(row[4]) == (len(run.gains) if scenario else 0), where


def compare(binary):
    clips = [soundbank.Clip(label * 3 + i, label, 0, 0.8 + i * 0.7, 0.0, 0.0)
             for label in range(50) for i in range(3)]
    sparse = [soundbank.Clip(row, label, 0, duration, 0.0, 0.0) for row, label, duration in
              ((1, 1, 0.8), (2, 1, 1.5), (3, 5, 2.0), (4, 7, 3.8), (8, 11, 2.2))]
    with subprocess.Popen([binary], stdout=subprocess.PIPE, text=True) as process:
        lines = iter(process.stdout)
        for rung in range(-1, 35):
            for seed in range(-3, 6):
                emit_expected(lines, rung, seed, "tune")
            for records in (clips, sparse):
                tuner._clips.clear()
                with patch.object(soundbank, "bank", return_value=records):
                    emit_expected(lines, rung, 17, "esc50")
        emit_expected(lines, 30, -(2**63), "tune")
        emit_expected(lines, 30, 2**63 - 1, "tune")
        emit_expected(lines, 20, 17, "tune", 1)
        emit_expected(lines, 20, 17, "tune", 2)
        assert next(lines, None) is None
        assert process.wait() == 0
    print("PASS: 400 Tuner deals and control replays match Python")


if __name__ == "__main__":
    compare(sys.argv[1])
