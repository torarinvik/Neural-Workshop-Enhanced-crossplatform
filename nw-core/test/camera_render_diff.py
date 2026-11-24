"""Verify the Camera frame and mesh wire format consumed by the render hosts."""
import math
from random import Random
import struct
import subprocess
import sys

from camera_diff import camera


def near(values, expected):
    assert len(values) == len(expected)
    assert all(math.isclose(a, b, abs_tol=1e-6, rel_tol=1e-6)
               for a, b in zip(values, expected)), (values, expected)


def check_frame(packet, scene, peek):
    magic, version, width, height, passes, count, field = struct.unpack_from("<4s5If", packet)
    assert (magic, version, width, height) == (b"NWCF", 1, 881, 641)
    assert (passes, count) == (1 if peek else 2, len(scene.things) + 2)
    assert len(packet) == 216 + passes * 92 + count * 96
    near((field,), (scene.level.field,))
    assert all(map(math.isfinite, struct.unpack_from("<47f", packet, 28)))

    offset = 216
    rects = []
    for pose in ((scene.target,) if peek else (scene.start, scene.target)):
        x, y, w, h, *values = struct.unpack_from("<4I19f", packet, offset)
        assert w >= 8 and h >= 8 and x + w <= width and y + h <= height
        near(values[:3], pose[:3])
        assert all(map(math.isfinite, values[3:]))
        rects.append((x, y, w, h))
        offset += 92
    if len(rects) == 2:
        (x, y, w, h), (px, py, pw, ph) = rects
        assert x < px < px + pw < x + w and y < py < py + ph < y + h
    assert struct.unpack_from("<2I", packet, offset) == (7, 0)
    assert struct.unpack_from("<2I", packet, offset + 96) == (6, 0)
    for index, thing in enumerate(scene.things, start=2):
        kind, casts, *values = struct.unpack_from("<2I22f", packet, offset + 96 * index)
        assert (kind, casts) == (camera.SHAPES.index(thing.shape), 1)
        near(values[12:16], (thing.x, 0.0, thing.z, 1.0))
        near(values[-3:], thing.colour)
    return rects[0], packet[offset:]


def check_mesh(kind, packet, field):
    magic, version, actual_kind, count, indices = struct.unpack_from("<4s4I", packet)
    assert (magic, version, actual_kind) == (b"NWCM", 1, kind)
    assert count > 0 and indices > 0 and indices % 3 == 0
    offset = 20 + count * 24
    assert len(packet) == offset + indices * 4
    vertices = struct.unpack_from(f"<{count * 6}f", packet, 20)
    assert all(map(math.isfinite, vertices))
    assert max(struct.unpack_from(f"<{indices}I", packet, offset)) < count
    if kind in (6, 7):
        half = field if kind == 6 else field * 6 + 60
        assert count == 4 and indices == 6
        near((max(vertices[0::6]), max(vertices[2::6])), (half, half))


def main(binary):
    packets = [bytes.fromhex(line) for line in subprocess.check_output([binary], text=True).splitlines()]
    assert len(packets) == 10
    scene = camera.deal(8, rng=Random(17))
    assert scene is not None
    normal = check_frame(packets[0], scene, False)
    peek = check_frame(packets[1], scene, True)
    assert normal == peek
    for kind, packet in enumerate(packets[2:]):
        check_mesh(kind, packet, scene.level.field)
    print("PASS: 10 Camera frame and mesh packets")


if __name__ == "__main__":
    main(sys.argv[1])
