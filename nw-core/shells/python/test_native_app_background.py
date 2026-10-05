"""Theme backing-color contract for the native Pyglet shell."""

from __future__ import annotations

import sys
from pathlib import Path

SHELL = Path(__file__).resolve().parent
sys.path.insert(0, str(SHELL))

from app import window_background_rgba  # noqa: E402


def test_theme_backing_matches_source_text_contrast() -> None:
    light = type("Session", (), {"black_background": False})()
    dark = type("Session", (), {"black_background": True})()
    assert window_background_rgba(light) == (1.0, 1.0, 1.0, 1.0)
    assert window_background_rgba(dark) == (0.0, 0.0, 0.0, 1.0)


if __name__ == "__main__":
    test_theme_backing_matches_source_text_contrast()
    print("PASS: native app light/dark backing colors match source theme")
