#!/usr/bin/env python3
"""Differential harness: stats.elisa vs bwaccel/fallback.py's stats kernels."""
import importlib.util
import math
import subprocess
import sys

REF = ("/Users/torarinvikbjarko/Documents/Coding Projects/Python Projects/"
       "neural-workshop-enhanced/bwaccel/fallback.py")

spec = importlib.util.spec_from_file_location("ref_fallback", REF)
ref = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ref)

FULL = ("2024-03-15 09:30:00,D2B,85,2,3,10,20,0,1,11,12,13,14,15,16,17,18,19,"
        "20,21,22,23,24,25,26,123.7\n"
        "2024-03-15 10:00:05,D2B,90,2,4,10,20,1,2,31,32,33,34,35,36,37,38,39,"
        "40,41,42,43,44,45,46,58.4\n")
TABS = ("2024-04-01 08:00:00\tD2B\t70\t2\t2\t10\t20\t0\t1\t1\t2\t3\t4\t5\t6\t7"
        "\t8\t9\t10\t11\t12\t13\t14\t15\t16\t99.5\n")
JUNK = ("# a comment\n"
        "2024-05-01 07:00:00,D2B,60,2,2,10,20,0,1\n"
        "short\n"
        "2024\n"
        "XX24-05-01 07:00:00,D2B,60,2,2,10,20,0,1\n"
        "2024-5X-01 07:00:00,D2B,60,2,2,10,20,0,1\n"
        "2024-05-02 07:00:00,D2B,61,2,2,10,20,0\n")
CRLF = ("2024-06-01 12:00:00,D2B,55,2,2,10,20,0,1,1,2,3,4,5,6,7,8,9,10,11,12,"
        "13,14,15,16,10.5\r\n\r\n"
        "2024-06-01 13:00:00,D2B,65,2,2,10,20,0,2,1,2,3,4,5,6,7,8,9,10,11,12,"
        "13,14,15,16,20.4")
LOOSE = ("2024-07-01 06:00:00,D2B, 42 ,2,x,10,20,0,1,1,2,3,4,5,6,7,8,9,10,11,"
         "12,13,14,15,16, 2.5 \n"
         "2024-07-01 06:30:00,D2B,43,2,2,10,20,0,1,1,2,3,4,5,6,7,8,9,10,11,12,"
         "13,14,15,16,3.5\n"
         "2024-07-01 07:00:00,D2B,44,2,2,10,20,0,1,1,2,3,4,5,6,7,8,9,10,11,12,"
         "13,14,15,16,nonsense\n")
MIN9 = "2024-08-01 05:00:00,D2B,50,2,2,10,20,0,7\n"

BODIES = (("full", FULL), ("tabs", TABS), ("junk", JUNK), ("crlf", CRLF),
          ("loose", LOOSE), ("min9", MIN9), ("empty", ""))


def python_lines():
    out = []
    for tag, body in BODIES:
        records = ref._parse_stats_text_py(body)
        out.append(f"{tag},{len(records)}")
        for r in records:
            fields = [r['year'], r['month'], r['day'], r['hour'], r['minute'],
                      r['second'], r['percent'], r['mode'], r['nback'],
                      r['ticks'], r['trials'], r['manual'], r['session'],
                      r['sesstime']] + list(r['cats'])
            out.append("  rec," + ",".join(str(v) for v in fields))

    for style in (0, 1, 2, 3, 4):
        for count in (0, 1, 4):
            entries = [(float(2 + i), float(40 + 17 * i)) for i in range(count)]
            mean, best = ref._aggregate_day_scores_py(style, entries, 80.0, 50.0)
            out.append(f"agg,{style},{count},"
                       f"{int(math.trunc(mean * 100000.0))},"
                       f"{int(math.trunc(best * 100000.0))}")
    return out


def main():
    got = [ln for ln in subprocess.run([sys.argv[1]], capture_output=True, text=True,
                                       check=True).stdout.splitlines() if ln.strip()]
    want = python_lines()
    if len(got) != len(want):
        print(f"FAIL: line count {len(got)} vs {len(want)}")
        for g, w in list(zip(got, want))[:6]:
            print(f"  elisa:  {g}\n  python: {w}")
        return 1
    bad = [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w]
    for i, g, w in bad[:8]:
        print(f"MISMATCH line {i}\n  elisa:  {g}\n  python: {w}")
    if bad:
        print(f"FAIL: {len(bad)}/{len(want)} mismatches")
        return 1
    print(f"PASS: {len(want)} cases identical")
    return 0


if __name__ == "__main__":
    sys.exit(main())
