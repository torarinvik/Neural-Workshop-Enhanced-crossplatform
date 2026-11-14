#!/usr/bin/env python3
"""Capture the original Graph Mapping UI for a deterministic controller frame.

The frame JSON is produced by graphmapping_visual_fixture.mjs from the same
seed/options used by the browser. The original checkout remains read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

NW_CORE = Path(__file__).resolve().parents[1]
ORIGINAL = NW_CORE.parent / "original-neural-workshop-enhanced"
REFERENCE_PYTHON = ORIGINAL / ".venv" / "bin" / "python"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame", required=True, type=Path)
    parser.add_argument("--png", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--width", type=int, default=912,
                        help="reference window width in points")
    parser.add_argument("--height", type=int, default=684,
                        help="reference window height in points")
    parser.add_argument("--theme", choices=("light", "dark"), default="light")
    args = parser.parse_args()
    args.frame = args.frame.resolve()
    args.png = args.png.resolve()
    args.metadata = args.metadata.resolve()
    if (args.width < 1 or args.height < 1 or
            not args.frame.is_file()):
        parser.error("viewport dimensions must be positive and --frame must exist")

    # Reenter the frozen source venv directly. scenediff.reexec is for sweep
    # scripts whose first argument is a compiled binary; this helper takes
    # named flags, so preserve argv and install the same source recorder setup
    # here instead.
    if (REFERENCE_PYTHON.is_file() and os.path.realpath(sys.executable) !=
            os.path.realpath(REFERENCE_PYTHON)):
        os.execv(str(REFERENCE_PYTHON),
                 [str(REFERENCE_PYTHON), str(Path(__file__).resolve()),
                  *sys.argv[1:]])
    sys.path.insert(0, str(NW_CORE / "test"))
    sys.path.insert(0, str(ORIGINAL / "tests"))
    os.chdir(ORIGINAL)
    import framerec
    framerec.install()
    import uisupport
    if uisupport.UI_IMPORT_ERROR is not None:
        raise SystemExit(f"UI_IMPORT_ERROR: {uisupport.UI_IMPORT_ERROR}")

    import pyglet
    from pyglet.gl import glClearColor
    from pyglet.image import ImageData
    from nwenv.frames import capture_rgba
    from neural_workshop import display, geometry, state
    from neural_workshop.ui.graphmapping import Graph, GraphMapping

    fixture = json.loads(args.frame.read_text())
    for overlay in list(display.open_overlays()):
        overlay.close()
    state.cfg.BLACK_BACKGROUND = args.theme == "dark"
    actual_points = geometry.set_window_size(args.width, args.height)
    if actual_points != (args.width, args.height):
        raise SystemExit(
            f"requested {args.width}x{args.height} points, got {actual_points}")
    display.relayout()

    screen = GraphMapping()
    screen.graphs = [Graph(int(graph["size"]), tuple(
        (int(edge[0]), int(edge[1])) for edge in graph["edges"]))
        for graph in fixture["graphs"]]
    screen.spots = [[(float(point["x"]), float(point["y"]))
                     for point in panel] for panel in fixture["spots"]]
    screen.trial = int(fixture["trial"])
    screen.total_trials = int(fixture["totalTrials"])
    screen.correct = int(fixture["correct"])
    screen.phase = str(fixture["phase"])
    screen.message = str(fixture["message"])
    screen.verdict_shown = None
    screen._build_chrome()

    window = state.window
    window.switch_to()
    clear = 0.0 if args.theme == "dark" else 1.0
    glClearColor(clear, clear, clear, 1.0)
    window.dispatch_events()
    window.clear()
    screen.on_draw()
    width, height, rgba = capture_rgba(window)
    if width <= 0 or height <= 0 or not rgba:
        screen.close()
        raise SystemExit("original Graph Mapping framebuffer capture is empty")

    args.png.parent.mkdir(parents=True, exist_ok=True)
    args.metadata.parent.mkdir(parents=True, exist_ok=True)
    ImageData(width, height, "RGBA", rgba, pitch=-width * 4).save(str(args.png))
    metadata = {
        "captureComplete": True,
        "renderer": "original-pyglet-ui",
        "fixture": str(args.frame),
        "fixtureSha256": hashlib.sha256(args.frame.read_bytes()).hexdigest(),
        "viewportPoints": [args.width, args.height],
        "framebufferPixels": [width, height],
        "theme": args.theme,
        "phase": fixture["phase"],
        "nodes": fixture["nodes"],
        "edgeCounts": [len(graph["edges"]) for graph in fixture["graphs"]],
        "pngSha256": hashlib.sha256(args.png.read_bytes()).hexdigest(),
    }
    args.metadata.write_text(json.dumps(metadata, indent=2) + "\n")
    screen.close()
    window.close()
    print(f"graphmapping_reference_capture: PASS ({args.png})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
