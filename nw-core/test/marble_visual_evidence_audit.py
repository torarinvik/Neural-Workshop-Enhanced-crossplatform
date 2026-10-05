"""Revalidate current Marble capture pairs; never infer visual acceptance."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

PAIRS = (
    ("mm-source-dpr1-release", "mm-browser-dpr1-release"),
    ("mm-source-physical-loss-current", "mm-browser-physical-loss-current"),
    ("mm-source-physical-win-current", "mm-browser-physical-win-current"),
    ("mm-source-physical-done-current", "mm-browser-physical-done-current"),
    ("mm-source-timeout-current", "mm-browser-timeout-current"),
    ("mm-source-ready-current", "mm-browser-ready-current"),
    ("mm-clean-oct3-source-r16-dark-east30", "mm-clean-oct3-browser-r16-dark-east30"),
    ("mm-clean-oct3-source-r16-release", "mm-clean-oct3-browser-r16-release"),
    ("mm-clean-oct3-source-r16-restart", "mm-clean-oct3-browser-r16-restart"),
    ("mm-nexttrial200-f32-source", "mm-nexttrial200-f32-browser"),
    ("mm-nexttrial200-f32-source", "mm-nexttrial200-auto-browser"),
    ("mm-source-r16-800x600-release", "mm-browser-r16-800x600-release-framebuffer"),
    ("mm-source-r16-800x600-release", "mm-helper-800x600-release"),
    ("mm-source-ready-current", "mm-browser-ready-current-composited"),
    ("mm-source-b903-r16-running", "mm-browser-b903-r16-running"),
    ("marble-dfaeb-matched-20261004/source-r16-seed17",
     "marble-dfaeb-matched-20261004/browser-r16-seed17"),
    ("marble-dfaeb-matched-20261004/dark-tilt/source-r16-seed17-dark-tilt",
     "marble-dfaeb-matched-20261004/dark-tilt/browser-r16-seed17-dark-tilt"),
    ("marble-collar-current-pair-20261004/source-r16-run17-collar",
     "marble-collar-current-pair-20261004/browser-r16-run17-collar"),
    ("marble-current-pair-20261004/source-r16-seed17",
     "marble-current-pair-20261004/browser-r16-seed17"),
    ("marble-current-pair-20261004/dark-tilt/source-r16-seed17-east30",
     "marble-current-pair-20261004/dark-tilt/browser-r16-seed17-east30"),
    ("marble-current-pair-20261004/dark-tilt/source-r16-seed17-east30-restart",
     "marble-current-pair-20261004/dark-tilt/browser-r16-seed17-east30-restart"),
    ("marble-current-pair-20261004/dpr1-light-tilt/source-r16-seed17-east30",
     "marble-current-pair-20261004/dpr1-light-tilt/browser-r16-seed17-east30"),
    ("marble-current-pair-20261004/dpr1-dark-tilt/source-r16-seed17-east30",
     "marble-current-pair-20261004/dpr1-dark-tilt/browser-r16-seed17-east30"),
    ("mm-loss-current-20261005-source", "mm-loss-current-20261005-browser"),
    ("mm-win-current-20261005-source", "mm-win-current-20261005-browser"),
    ("mm-done-current-20261005-source", "mm-done-current-20261005-browser"),
    ("mm-clearance-partial-loss-current-20261005-source",
     "mm-clearance-partial-loss-current-20261005-browser"),
    ("mm-clearance-dpr1-dark-current-20261005-source",
     "mm-clearance-dpr1-dark-current-20261005-browser"),
    ("mm-clearance-wide-dpr1-dark-current-20261005-source",
     "mm-clearance-wide-dpr1-dark-current-20261005-browser"),
    ("mm-clearance-wide-dpr1-light-current-20261005-source",
     "mm-clearance-wide-dpr1-light-current-20261005-browser"),
    ("mm-clearance-ready-wide-dpr1-light-current-20261005-source",
     "mm-clearance-ready-wide-dpr1-light-current-20261005-browser"),
    ("mm-clearance-wide-dpr1-light-physical-win-trace-20261005-source",
     "mm-clearance-wide-dpr1-light-physical-win-trace-20261005-browser"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", required=True, action="append", type=Path,
                        help="capture root; repeat when fixtures are stored in multiple roots")
    parser.add_argument("--output", type=Path,
                        help="optional path for a durable JSON audit receipt")
    args = parser.parse_args()
    comparator = Path(__file__).with_name("marble_render_pair_test.py")
    roots = [root.resolve() for root in args.artifacts]
    entries, failures = [], []
    for reference, candidate in PAIRS:
        # CSS element screenshot is explicitly excluded from the valid pair.
        candidate_metadata = candidate.removesuffix("-framebuffer")
        required_by_root = [(root, (
            root / f"{reference}.png",
            root / f"{candidate}.png",
            root / f"{reference}.json",
            root / f"{candidate_metadata}.json",
        )) for root in roots]
        resolved = next(((root, paths) for root, paths in required_by_root
                         if all(path.is_file() for path in paths)), None)
        if resolved is None:
            root, required = min(
                required_by_root,
                key=lambda item: sum(not path.is_file() for path in item[1]))
            missing = [path.name for path in required if not path.is_file()]
            failures.append({"reference": reference, "candidate": candidate,
                             "error": "missing artifact(s): " + ", ".join(missing) +
                                      f"; no single root contains the pair (closest: {root})",
                             "stderr": ""})
            continue
        root, required = resolved
        command = [sys.executable, str(comparator),
                   str(required[0]), str(required[1]),
                   "--reference-metadata", str(required[2]),
                   "--candidate-metadata", str(required[3]),
                   "--require-synchronized", "--require-scene-state", "--json"]
        result = subprocess.run(command, capture_output=True, text=True)
        try:
            verdict = json.loads(result.stdout)
            if not isinstance(verdict, dict):
                raise ValueError("comparator receipt must be a JSON object")
            if result.returncode or verdict.get("failures") != [] or \
                    verdict.get("result") != "diagnostic-only":
                raise ValueError("pair did not produce a clean diagnostic verdict")
            metadata = json.loads(required[2].read_text())
            if not isinstance(metadata, dict) or not isinstance(metadata.get("sceneState"), dict):
                raise ValueError("reference metadata must contain a scene-state object")
            entries.append({"reference": reference, "candidate": candidate,
                            "phase": metadata["sceneState"]["phase"],
                            "terminalFixture": metadata.get("terminalFixture", "unrecorded"),
                            "theme": metadata["theme"], "dpr": metadata["dpr"],
                            "rung": metadata["rung"],
                            "dimensions": metadata["image"]["dimensions"],
                            "candidateReadback": verdict.get("candidateReadback"),
                            "metrics": verdict["metrics"],
                            "stage": verdict["regions"]["stage"]})
        except (ValueError, KeyError, TypeError, OSError) as error:
            failures.append({"reference": reference, "candidate": candidate,
                             "error": str(error), "stderr": result.stderr})
    report = {"pairs": entries, "failures": failures,
              "accepted": False,
              "scope": "listed captures only; no completeness or shipping claim",
              "outstanding": ["reviewed pixel policy",
                              "broader DPR1 phase/theme/viewport coverage",
                              "additional current-artifact lifecycle coverage",
                              "shipping build qualification"]}
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return int(bool(failures))


if __name__ == "__main__":
    raise SystemExit(main())
