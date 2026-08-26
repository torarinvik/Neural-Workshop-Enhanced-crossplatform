"""Read the ORIGINAL's title screen and normalise it to reference space.

Run with the original's own interpreter -- it needs pyglet and a GL context:

    <original>/.venv/bin/python scripts/extract_title.py [--black] [--jaeggi] [--clinical]

Two things this exists to get right, both of which a careful reading of hud.py
gets WRONG:

  * the window pyglet hands back is retina-doubled here, so every geometry
    helper returns physical pixels and each number in hud.py lays out at twice
    its written value. Everything below is divided by the window's own measured
    scale rather than by an assumed factor.
  * the key list is assembled from two flags, so the only way to know what a
    build actually offers is to set the flags and rebuild the label.
"""
import json
import sys

sys.path.insert(0, "tests")
import uisupport  # noqa: E402  (must import before neural_workshop)

if uisupport.UI_IMPORT_ERROR is not None:
    print("UI_IMPORT_ERROR: %s" % (uisupport.UI_IMPORT_ERROR,), file=sys.stderr)
    raise SystemExit(2)

from neural_workshop import geometry, state  # noqa: E402
from neural_workshop.ui import hud  # noqa: E402

black = "--black" in sys.argv
jaeggi = "--jaeggi" in sys.argv
clinical = "--clinical" in sys.argv

# COLOR_TEXT is not a module attribute: configdefaults keeps it INSIDE the
# config-file template string, so it only exists once the parser has read that
# template. Both variants are therefore taken off the live cfg.
state.cfg.BLACK_BACKGROUND = black
state.cfg.COLOR_TEXT = state.cfg.COLOR_TEXT_BLK if black else (0, 0, 0, 255)
state.cfg.JAEGGI_MODE = jaeggi
hud.CLINICAL_MODE = clinical

message = hud.TitleMessageLabel()
keys = hud.TitleKeysLabel()

W, H = geometry._width(), geometry._height()
SX, SY = W / 912.0, H / 684.0


def lab(label):
    return dict(text=label.text, x=label.x / SX, y=label.y / SY,
                size=label.font_size / SY, color=list(label.color),
                anchor="%s_%s" % (label.anchor_x, label.anchor_y))


graphic = state.brain_graphic
print(json.dumps(dict(
    physical=[W, H],
    title=lab(message.label), version=lab(message.label2),
    native=lab(message.native), space=lab(keys.space), keys=lab(keys.keys),
    key_lines=keys.keys.text.split("\n"),
    key_line_height=(keys.keys.content_height / len(keys.keys.text.split("\n"))) / SY,
    splash=dict(x=graphic.x / SX, y=graphic.y / SY,
                w=graphic.width / SX, h=graphic.height / SY),
    black_background=black, jaeggi=jaeggi, clinical=clinical,
), indent=1))
