"""Read the ORIGINAL's Menu chrome and normalise it to reference space.

    <original>/.venv/bin/python scripts/extract_menu.py --options N --select K [--black]

Every menu screen in the game is one Menu instance, so measuring the class
measures all of them. Same retina caveat as extract_title.py: divide by the
window's own scale rather than assuming.
"""
import json
import sys

sys.path.insert(0, "tests")
import uisupport  # noqa: E402

if uisupport.UI_IMPORT_ERROR is not None:
    print("UI_IMPORT_ERROR: %s" % (uisupport.UI_IMPORT_ERROR,), file=sys.stderr)
    raise SystemExit(2)

from neural_workshop import geometry, state  # noqa: E402
from neural_workshop.ui.menu import Menu  # noqa: E402


def arg(name, default):
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


count = arg("--options", 8)
select = arg("--select", 0)
black = "--black" in sys.argv

state.cfg.BLACK_BACKGROUND = black
options = ["Option %d" % i for i in range(count)]
menu = Menu(options, title="Test Menu")
menu.move_selection(select, relative=False)

W, H = geometry._width(), geometry._height()
SX, SY = W / 912.0, H / 684.0


def lab(label):
    return dict(text=label.text, x=label.x / SX, y=label.y / SY,
                size=label.font_size / SY, color=list(label.color),
                anchor="%s_%s" % (label.anchor_x, label.anchor_y))


# pyglet keeps the polygon's points as a list of (x, y) tuples.
raw = getattr(menu.marker, "_coordinates", None)
marker = [[p[0] / SX, p[1] / SY] for p in raw] if raw else None

out = dict(
    physical=[W, H],
    title=lab(menu.title), footnote=lab(menu.footnote),
    rows=[lab(l) for l in menu.labels],
    pagesize=menu.pagesize, disppos=menu.disppos, selpos=menu.selpos,
    choicesize=menu.choicesize / SY,
    bgcolor=list(menu.bgcolor), textcolor=list(menu.textcolor),
    marker=marker, marker_color=list(menu.marker.color),
    options=options, black_background=black,
)
menu.close()
print(json.dumps(out, indent=1))
