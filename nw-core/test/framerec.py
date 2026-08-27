# -*- coding: utf-8 -*-
"""Recording what the reference actually draws, as a display list.

The port's scene layer has to emit the same frame the pyglet UI draws, and
"the same" has to mean something a machine can check. This is what makes it
checkable: it wraps the handful of pyglet classes the UI builds its widgets
out of, keeps every one that is made, and reads their live attributes back on
demand as one canonical text frame.

Why constructors and not the batch. pyglet 2 stores a Batch as vertex domains,
not as the objects that fed them, so walking a batch gets triangles with the
kind, the text and the anchor already melted out of them. And the UI has "no
per-frame layout pass" -- widgets are built once and then mutated -- so the
objects themselves ARE the retained frame. Wrapping the constructor keeps the
object; reading it at capture time keeps the mutation.

Nothing here is imported by the game. It is installed by a test before
`bootstrap.build_application()` runs, and the game goes on calling
`pyglet.shapes.Rectangle` exactly as it did -- every use is an attribute lookup
on the module at call time, and none of the fifty-eight UI modules from-imports
a drawing class. That was checked rather than assumed.

Two things this deliberately does NOT do:

  * It does not try to reproduce pyglet's draw ORDER. Within a batch that order
    is by group and then by vertex domain, which is an implementation detail of
    the renderer and not a fact about the frame. Commands come out ordered by
    (group order, creation serial), which is stable, and the port is written to
    match it.
  * It does not read pixels. A pixel comparison across two renderers measures
    the renderers; this measures the frame.

SPDX-License-Identifier: GPL-2.0-or-later
"""
from __future__ import annotations

import itertools
import weakref

import pyglet

#: Live widgets, oldest first. Weak, so a scene that tears itself down between
#: trials leaves nothing behind to be drawn twice.
_LIVE: "list[tuple[int, str, weakref.ref, dict]]" = []

_SERIAL = itertools.count()

#: What was patched, so `uninstall` can put it back.
_PATCHED: "list[tuple[object, str, object]]" = []

#: Kinds, in the display list's own numbering (src/display.elisa).
KIND = {
    "Rectangle": 1, "BorderedRectangle": 2, "Box": 3, "Circle": 4, "Arc": 5,
    "Line": 6, "Triangle": 7, "Polygon": 8, "Sprite": 10, "Label": 11,
    "MultiLine": 16, "Star": 17,
}


def _register(obj, kind, extra=None):
    _LIVE.append((next(_SERIAL), kind, weakref.ref(obj), extra or {}))


def _wrap(module, name):
    original = getattr(module, name)

    class Recorded(original):                       # noqa: D401
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            keep = {}
            if name in ("Polygon", "MultiLine"):
                # Variable-length, and pyglet keeps only the flattened form.
                keep["coordinates"] = [tuple(one) for one in args]
            _register(self, name, keep)

    Recorded.__name__ = original.__name__
    Recorded.__qualname__ = original.__qualname__
    setattr(module, name, Recorded)
    _PATCHED.append((module, name, original))
    return Recorded


def install():
    """Wrap the drawing classes. Call BEFORE the application is built."""
    if _PATCHED:
        return
    for name in ("Rectangle", "BorderedRectangle", "Box", "Circle", "Arc",
                 "Line", "Triangle", "Polygon", "MultiLine", "Star"):
        _wrap(pyglet.shapes, name)
    _wrap(pyglet.text, "Label")
    _wrap(pyglet.sprite, "Sprite")


def uninstall():
    for module, name, original in reversed(_PATCHED):
        setattr(module, name, original)
    _PATCHED.clear()
    _LIVE.clear()


def forget():
    """Drop every recorded widget without unpatching."""
    _LIVE.clear()


def _group_order(group):
    """A group's depth-first order key, outermost first.

    pyglet orders a batch by the group chain, so the key has to be the chain
    and not the leaf: two groups at order 0 under different parents are not
    the same depth.
    """
    chain = []
    while group is not None:
        chain.append(getattr(group, "order", 0))
        group = getattr(group, "parent", None)
    return tuple(reversed(chain))


#: Physical-pixels-per-reference-unit, set by `set_scale`. The window pyglet
#: hands back here is retina-doubled, so every geometry helper returns physical
#: pixels and each number written in the UI lays out at twice its value. Every
#: extractor in this repo divides by the window's OWN measured scale rather
#: than by an assumed factor, and so does this.
_SCALE = [1.0, 1.0]


def set_scale(sx, sy):
    _SCALE[0] = float(sx)
    _SCALE[1] = float(sy)


def _number(value, axis=None):
    """A float printed the way the sweep prints one: exactly.

    *axis* is 0 for an x-ish measure, 1 for a y-ish one, None for a pure
    number. A radius, a thickness and a font size all take the y scale, which
    is what `extract_title.py` does and what the layout maths assumes.
    """
    value = float(value)
    if axis is not None:
        value = value / _SCALE[axis]
    return repr(value)


def _color(obj):
    color = tuple(getattr(obj, "color", (255, 255, 255, 255)))
    if len(color) == 3:
        color = color + (int(getattr(obj, "opacity", 255)),)
    return "%d.%d.%d.%d" % color


def _visible(obj):
    if not getattr(obj, "visible", True):
        return False
    return int(getattr(obj, "opacity", 255)) > 0


#: Which live attributes make up each kind, beyond x/y/colour, and which axis
#: each is measured on. None means the number is not a length: a segment count,
#: an angle in degrees and a spike count are all scale-free.
_FIELDS = {
    "Rectangle": (("width", 0), ("height", 1), ("rotation", None)),
    "BorderedRectangle": (("width", 0), ("height", 1), ("border", 1)),
    "Box": (("width", 0), ("height", 1), ("thickness", 1)),
    "Circle": (("radius", 1), ("segments", None)),
    "Arc": (("radius", 1), ("segments", None), ("angle", None),
            ("start_angle", None), ("thickness", 1)),
    "Line": (("x2", 0), ("y2", 1), ("thickness", 1)),
    "Triangle": (("x2", 0), ("y2", 1), ("x3", 0), ("y3", 1)),
    "Star": (("outer_radius", 1), ("inner_radius", 1),
             ("num_spikes", None), ("rotation", None)),
    "MultiLine": (("thickness", 1),),
}


def _label_cells(obj):
    out = [
        repr(obj.text),
        str(obj.font_name),
        _number(obj.font_size or 0.0, 1),
        str(obj.anchor_x), str(obj.anchor_y),
        # pyglet 2.1 replaced `bold` with a named weight; the reference asks
        # for bold in three places and the name is what it now stores.
        str(getattr(obj, "weight", "normal")),
        "1" if getattr(obj, "italic", False) else "0",
        "1" if getattr(obj, "multiline", False) else "0",
        _number(getattr(obj, "width", None) or 0.0, 0),
        str(obj.document.get_style("align") or "left"),
        _number(getattr(obj, "content_width", 0.0), 0),
        _number(getattr(obj, "content_height", 0.0), 1),
    ]
    return out


def _sprite_cells(obj):
    image = obj.image
    return [
        _number(getattr(obj, "scale", 1.0)),
        _number(getattr(obj, "rotation", 0.0)),
        str(getattr(image, "width", 0)), str(getattr(image, "height", 0)),
    ]


def capture(want_invisible=False):
    """Every live widget as one canonical line apiece, in frame order."""
    rows = []
    keep = []
    for serial, kind, ref, extra in _LIVE:
        obj = ref()
        if obj is None:
            continue
        keep.append((serial, kind, ref, extra))
        if not want_invisible and not _visible(obj):
            continue
        cells = [str(KIND[kind]), _number(obj.x, 0), _number(obj.y, 1),
                 _color(obj)]
        if kind == "Label":
            cells.extend(_label_cells(obj))
        elif kind == "Sprite":
            cells.extend(_sprite_cells(obj))
        elif kind == "Polygon":
            for point in extra.get("coordinates", ()):
                cells.extend(_number(one, at) for at, one in enumerate(point))
        else:
            for field, axis in _FIELDS.get(kind, ()):
                cells.append(_number(getattr(obj, field, 0) or 0, axis))
            if kind == "MultiLine":
                for point in extra.get("coordinates", ()):
                    cells.extend(_number(one, at)
                                 for at, one in enumerate(point))
        rows.append((_group_order(getattr(obj, "group", None)), serial,
                     "|".join(cells)))
    _LIVE[:] = keep
    rows.sort(key=lambda row: (row[0], row[1]))
    return [row[2] for row in rows]
