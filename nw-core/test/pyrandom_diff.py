#!/usr/bin/env python3
"""Differential harness: pyrandom.elisa vs CPython's own random module.

The Elisa side must consume the Mersenne Twister stream in exactly the same
order as CPython, so any divergence in getrandbits / _randbelow / shuffle /
sample shows up as a mismatch here rather than as a subtly different game.
"""
import random
import subprocess
import sys


def as_signed(value):
    """Print 64-bit draws the way the Elisa side casts them (u64 -> i64)."""
    return value - (1 << 64) if value >= (1 << 63) else value


def python_lines():
    out = []
    for seed in (0, 42, 1234567890123456789):
        for k in (1, 3, 8, 16, 31, 32, 33, 48, 64):
            random.seed(seed)
            draws = [as_signed(random.getrandbits(k)) for _ in range(4)]
            out.append(",".join(str(v) for v in ["grb", seed, k] + draws))

    for seed in (7, 99):
        for n in (1, 2, 3, 5, 8, 10, 16, 17, 100, 1000):
            random.seed(seed)
            draws = [random._inst._randbelow(n) for _ in range(6)]
            out.append(",".join(str(v) for v in ["rbl", seed, n] + draws))

    for seed in (3, 2024):
        for high in (1, 6, 8, 52, 1000):
            random.seed(seed)
            draws = [random.randint(1, high) for _ in range(6)]
            out.append(",".join(str(v) for v in ["ri", seed, high] + draws))

    for seed in (1, 42, 777):
        for count in (2, 3, 8, 20):
            random.seed(seed)
            values = list(range(count))
            random.shuffle(values)
            out.append(",".join(str(v) for v in ["sh", seed, count] + values))

    for seed in (5, 31337):
        for high in (4, 8, 21, 22, 30, 64, 200):
            for k in (1, 2, 5, 6, 7):
                if k > high:
                    continue
                random.seed(seed)
                picked = random.sample(range(1, high + 1), k)
                out.append(",".join(str(v) for v in ["sm", seed, high, k] + picked))
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True, text=True,
                                       check=True).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:5]:
            print(f"  elisa:  {g}\n  python: {w}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:10]:
        print(f"MISMATCH line {i}\n  elisa:  {g}\n  python: {w}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
