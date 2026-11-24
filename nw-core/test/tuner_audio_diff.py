"""Compare Tuner dialogue-free radio playback with the original mixer."""

from array import array
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import soundbank, tuner


def recording(lines, path, row, rate, channels):
    pcm = array("h", ((i * 931) % 65536 - 32768 for i in range(4000 * channels)))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(pcm.tobytes())
    clip = soundbank.Clip(row, 0, 0.017, 0.097, 1.0, -10.0)
    sound = tuner.Sound("esc50", (row,), 0, 0, speed=0.93, backward=True)
    with patch.object(soundbank, "_path", return_value=str(path)), patch.object(tuner, "_clip", return_value=clip):
        base = soundbank.samples(clip)
        expected = tuner.wave(sound)
    assert tuple(map(int, next(lines).split())) == (len(base), len(expected))
    actual = array("f", map(float, next(lines).split()))
    assert actual == expected, (row, rate, channels)


def main():
    lines = iter(subprocess.check_output([sys.argv[1]], text=True).splitlines())
    count = 0
    for rung in (1, 10, 16, 24, 32):
        for seed in range(7, 10):
            radio = tuner.deal(rung, seed, bank="tune")
            run = tuner.Run(radio)
            listen = radio.listen
            while run.t < listen + 2.0:
                controls = [tuner.DOWN if run.t < listen + 0.19 else tuner.UP]
                if run.t >= listen + 0.45 and len(run.plays) == 1:
                    run.replay()
                run.step(1 / 60, controls)
            assert len(run.plays) == 2
            windows = ((0.15, 0.37), (0.7, 0.92), (listen + 0.11, listen + 0.40),
                       (listen + 0.43, listen + 0.67), (listen + 1.94, listen + 2.19))
            for start, end in windows:
                actual = bytes.fromhex(next(lines))
                expected = tuner.mix(run, start, end)
                assert len(actual) == len(expected), (rung, seed, start, len(actual), len(expected))
                if actual != expected:
                    frame = next(i for i in range(len(expected)) if actual[i] != expected[i]) // 4
                    offset = frame * 4
                    raise AssertionError((rung, seed, start, frame,
                                          actual[offset:offset + 4].hex(), expected[offset:offset + 4].hex()))
                count += 1
    with TemporaryDirectory() as directory:
        for row, (rate, channels) in enumerate(((44100, 2), (32000, 1), (16000, 2))):
            recording(lines, Path(directory) / "clip.wav", row, rate, channels)
    assert next(lines, None) is None
    print(f"PASS: {count + 3} Tuner audio cases match Python ({count} radio windows and 3 recorded-clip conversions)")


if __name__ == "__main__":
    main()
