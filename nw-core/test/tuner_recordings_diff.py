"""Replay the installed ESC-50 bank against the original Python file reader."""

from array import array
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
import wave

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "original-neural-workshop-enhanced"))
from neural_workshop import datasets, soundbank, tuner

INDEX = ROOT / "nw-core" / "res" / "misc" / "esc50" / "index.tsv"


def run(binary, index, directory):
    return iter(subprocess.check_output([binary, str(index), str(directory)], text=True).splitlines())


def compare(binary):
    with TemporaryDirectory() as temporary:
        root = Path(temporary)
        directory = root / "esc50"
        directory.mkdir()
        fixture = root / "sample.wav"
        with wave.open(str(fixture), "wb") as handle:
            handle.setnchannels(2)
            handle.setsampwidth(2)
            handle.setframerate(8000)
            samples = array("h", ((i * 931) % 65536 - 32768 for i in range(2 * 40000)))
            handle.writeframes(samples.tobytes())
        with patch.object(soundbank, "index_path", return_value=str(INDEX)), patch.object(
                datasets, "datasets_dir", return_value=str(root)):
            rows = [clip for clip in soundbank._read_index() if soundbank.usable(clip)]
            assert len(rows) > 300
            for clip in rows[:299]:
                os.link(fixture, directory / f"{clip.row:07}.wav")
            assert list(run(binary, INDEX, directory)) == ["0"]
            for clip in rows[299:400]:
                os.link(fixture, directory / f"{clip.row:07}.wav")
            bank = soundbank.bank()
            assert len(bank) == 400
            radio = tuner.deal(24, 17)
            guide_row = radio.heard.ref[0]
            corrupt_row = next(station.sound.ref[0] for station in radio.stations
                               if station.sound.ref[0] != guide_row)
            corrupt = directory / f"{corrupt_row:07}.wav"
            corrupt.unlink()
            corrupt.write_bytes(b"RIFF\x04\x00\x00\x00WAVE")
            # An odd-length unknown chunk exercises RIFF word alignment.
            body = fixture.read_bytes()
            junk = b"JUNK\x03\x00\x00\x00abc\x00"
            guide = directory / f"{guide_row:07}.wav"
            guide.unlink()
            guide.write_bytes(body[:4] + (len(body) - 8 + len(junk)).to_bytes(4, "little") +
                              body[8:12] + junk + body[12:])
            lines = run(binary, INDEX, directory)
            assert int(next(lines)) == len(bank)
            for clip in bank:
                row, label, duration = next(lines).split()
                assert (int(row), int(label)) == (clip.row, clip.label), (row, label, clip)
                assert math.isclose(float(duration), clip.end - clip.start, rel_tol=0, abs_tol=1e-12)
            heard = tuner.wave(radio.heard)
            assert tuple(map(int, next(lines).split())) == (radio.heard.ref[0], len(heard))
            actual = array("f", map(float, next(lines).split()))
            assert len(actual) == len(heard)
            if actual != heard:
                frame, values = next((i, v) for i, v in enumerate(zip(actual, heard)) if v[0] != v[1])
                raise AssertionError((frame, values))
            for station in radio.stations:
                assert tuple(map(int, next(lines).split())) == (station.sound.ref[0], len(tuner.wave(station.sound)))
            play = tuner.Run(radio)
            while play.t < radio.listen + 0.4:
                play.step(1 / 60, [tuner.DOWN])
            assert bytes.fromhex(next(lines)) == tuner.mix(play, radio.listen - 0.1, radio.listen + 0.2)
            assert next(lines, None) is None
            bad_index = root / "invalid.tsv"
            shutil.copyfile(INDEX, bad_index)
            with bad_index.open("a") as handle:
                handle.write("bad index line\n")
            assert list(run(binary, bad_index, directory)) == ["0"]
            assert list(run(binary, root / "missing.tsv", directory)) == ["0"]
    print("PASS: 4 Tuner recording scenarios match the Python bank and WAV reader")


if __name__ == "__main__":
    compare(sys.argv[1])
