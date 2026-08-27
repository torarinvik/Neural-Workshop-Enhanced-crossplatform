#!/usr/bin/env python3
"""Checks the Elisa display-list encoder against an independent Python model.

The Elisa side builds a representative frame and prints it as hex; this script
decodes it with the reference decoder and compares against the frame described
below. A mismatch means either the encoder or the wire format has drifted.
"""
import subprocess
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from display_decode import canonical, decode  # noqa: E402

WHITE = (255, 255, 255, 255)

EXPECTED = [
    "rect anchor_x=0.0000 anchor_y=0.0000 color=0:0:0:255 h=684.0000 "
    "rotation=0.0000 w=912.0000 x=0.0000 y=0.0000",
    "box color=64:64:64:255 h=300.0000 thickness=2.0000 w=300.0000 x=306.0000 y=114.0000",
    "bordered_rect border=255:255:255:255 border_width=3.0000 color=0:128:255:255 "
    "h=100.0000 w=100.0000 x=406.0000 y=214.0000",
    "circle color=255:200:0:255 radius=24.0000 x=456.0000 y=264.0000",
    "arc color=128:128:128:255 radius=40.0000 start_angle=0.0000 sweep=180.0000 "
    "x=456.0000 y=264.0000",
    "line color=90:90:90:255 width=1.5000 x1=0.0000 x2=912.0000 y1=100.0000 y2=100.0000",
    "triangle color=255:0:255:255 x1=10.0000 x2=30.0000 x3=20.0000 y1=10.0000 "
    "y2=10.0000 y3=30.0000",
    "polygon color=10:200:10:255 points=3",
    "poly_point x=100.0000 y=100.0000",
    "poly_point x=140.0000 y=100.0000",
    "poly_point x=120.0000 y=140.0000",
    "sprite asset=7 color=255:255:255:255 image_h=48 image_w=64 "
    "rotation=90.0000 scale=1.5000 x=700.0000 y=500.0000",
    "text anchor=center_center bold=False color=255:255:255:255 size=18.0000 "
    "text=Position match x=456.0000 y=60.0000",
    "text anchor=left_top bold=False color=200:200:200:255 size=14.0000 "
    "text=N = 2 x=20.0000 y=650.0000",
    "text anchor=center_top bold=True color=255:255:0:255 size=12.0000 "
    "text=Trial 4 x=456.0000 y=620.0000",
    "rect anchor_x=20.0000 anchor_y=10.0000 color=1:2:3:255 h=20.0000 "
    "rotation=0.0000 w=40.0000 x=200.0000 y=300.0000",
    "rect anchor_x=20.0000 anchor_y=10.0000 color=4:5:6:255 h=20.0000 "
    "rotation=30.0000 w=40.0000 x=250.0000 y=320.0000",
    "sprite_fit asset=9 color=255:255:255:255 room_h=90.0000 room_w=120.0000 "
    "rotation=45.0000 x=800.0000 y=400.0000",
    "star color=255:128:0:255 inner=12.0000 outer=30.0000 rotation=18.0000 "
    "spikes=5 x=500.0000 y=400.0000",
    "multiline color=0:255:255:255 points=3 thickness=2.5000 x=60.0000 y=60.0000",
    "poly_point x=60.0000 y=60.0000",
    "poly_point x=80.0000 y=90.0000",
    "poly_point x=110.0000 y=70.0000",
    "sound asset=3 gain=0.8000",
    "verdict verdict=0",
    "marker text=trial-end",
]


def main():
    hex_text = subprocess.run([sys.argv[1]], capture_output=True, text=True,
                              check=True).stdout.strip()
    blob = bytes.fromhex(hex_text)
    commands = decode(blob)
    got = canonical(commands)

    if len(got) != len(EXPECTED):
        print(f"FAIL: {len(got)} commands vs {len(EXPECTED)} expected")
        for line in got:
            print("  " + line)
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, EXPECTED)) if g != w]
    for i, g, w in bad:
        print(f"MISMATCH command {i}\n  got:      {g}\n  expected: {w}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(EXPECTED)} mismatches")
        return 1
    print(f"PASS: {len(EXPECTED)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
