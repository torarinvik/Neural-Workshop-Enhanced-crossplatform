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
import struct
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
            elif name == "Triangle":
                # pyglet 2.1.16's Triangle.x2 getter returns `x + x2`: the
                # constructor stores the second vertex absolute and the getter
                # adds the anchor anyway. Line.x2 does NOT do this, so it is a
                # bug in the one class and not a convention.
                #
                #   Triangle(10, 20, 100, 200, 300, 400).x2  ->  110.0
                #   Line(10, 20, 100, 200).x2                ->  100.0
                #
                # Every arrowhead in the game is a Triangle, so a recorder that
                # trusted the getter would have mis-measured all of them by the
                # anchor -- and consistently, on both the reference and nothing
                # to compare it against, which is how it would have gone
                # unnoticed. The constructor's own numbers are kept instead,
                # plus wherever the shape has since been moved to.
                keep["vertices"] = [float(one) for one in args[:6]]
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
    _BATCHES.clear()


#: Batches in the order `on_draw` submits them, set by `set_batches`. A screen
#: that keeps more than one batch draws them in a fixed order that pyglet knows
#: nothing about -- the 3D Maze submits its map, then its corridor, then its
#: chrome -- so the recorder cannot work it out and is told. Empty means one
#: batch and no ordering to apply, which is every other screen.
_BATCHES = []


def set_batches(batches):
    """Name the batches in the order the screen draws them."""
    _BATCHES[:] = list(batches)


def _batch_order(obj):
    """Which batch this widget is in, as an index into `_BATCHES`.

    A widget in no named batch sorts FIRST rather than last, because with no
    batches named at all every widget lands here and the order is the serial
    order the recorder has always used.
    """
    if not _BATCHES:
        return -1
    batch = getattr(obj, "batch", None)
    for index, known in enumerate(_BATCHES):
        if batch is known:
            return index
    return -1


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


#: When true, every number is printed as the i32 its f32 bytes spell.
#:
#: The display list stores coordinates as f32 -- that IS the contract, and
#: comparing at f64 would compare a precision the format does not deliver and
#: fail on every command. Bits rather than a rounded decimal so that nothing is
#: compared at a tolerance: a coordinate half a float out is a layout bug, and
#: printing it to six places is how such a bug survives a suite.
_BITS = [False]


def set_scale(sx, sy):
    _SCALE[0] = float(sx)
    _SCALE[1] = float(sy)


def set_bits(on=True):
    _BITS[0] = bool(on)


def _number(value, axis=None):
    """A float printed the way the sweep prints one: exactly.

    *axis* is 0 for an x-ish measure, 1 for a y-ish one, None for a pure
    number. A radius, a thickness and a font size all take the y scale, which
    is what `extract_title.py` does and what the layout maths assumes.
    """
    value = float(value)
    if axis is not None:
        value = value / _SCALE[axis]
    if _BITS[0]:
        return str(struct.unpack("<i", struct.pack("<f", value))[0])
    return repr(value)


def _color(obj):
    color = tuple(getattr(obj, "color", (255, 255, 255, 255)))
    if len(color) == 3:
        color = color + (int(getattr(obj, "opacity", 255)),)
    return "%d.%d.%d.%d" % color


def _visible(obj):
    """Whether the shape puts anything on screen.

    Transparent is not the same as absent, and a BorderedRectangle is where
    that bites: Go draws its cursor as a rect with a fully transparent FILL and
    an opaque border. Reading opacity alone would drop that command, and the
    port -- which emits it, correctly -- would have looked wrong.
    """
    if not getattr(obj, "visible", True):
        return False
    if int(getattr(obj, "opacity", 255)) > 0:
        return True
    border = getattr(obj, "border_color", None)
    if not border:
        return False
    # A three-tuple border is opaque -- Go passes `border_color=(50, 120, 220)`
    # with no alpha at all, and requiring four components here dropped its
    # cursor from every frame.
    return len(border) < 4 or border[3] > 0


#: Which live attributes make up each kind, beyond x/y/colour, and which axis
#: each is measured on. None means the number is not a length: a segment count,
#: an angle in degrees and a spike count are all scale-free.
#: Fields the DISPLAY LIST carries. Anything pyglet knows and a command does
#: not is absent on purpose, and each absence is a decision:
#:
#:   * `segments` on a circle -- pyglet picks a count from the radius; the
#:     format names a circle and lets the shell tessellate it.
#:   * `rotation` on a rectangle -- the format has no field for it. `e` and `f`
#:     are free on a RECT and this is where it would go; nothing in the port
#:     needs it yet, and comparing a field the format cannot carry would fail
#:     every frame rather than find anything.
#:   * a label's italic, multiline, width and align -- the core resolves a
#:     multiline block into one command a line (see scene_title.elisa) rather
#:     than asking a shell to reproduce another toolkit's line spacing.
_FIELDS = {
    # A rectangle's ANCHOR is recorded because Lookout's squares set it: a
    # square drawn as a glyph is centred on its point, and x/y alone cannot
    # tell that from a corner-anchored one. Every other rectangle in the
    # workshop leaves it at (0, 0), so the two extra cells are zeros there.
    "Rectangle": (("width", 0), ("height", 1), ("anchor_x", 0),
                  ("anchor_y", 1)),
    "BorderedRectangle": (("width", 0), ("height", 1), ("border", 1)),
    # border_color is appended separately below: it is a colour, not a length.
    "Box": (("width", 0), ("height", 1), ("thickness", 1)),
    "Circle": (("radius", 1),),
    "Arc": (("radius", 1), ("start_angle", None), ("angle", None)),
    "Line": (("x2", 0), ("y2", 1), ("thickness", 1)),

    "Star": (("outer_radius", 1), ("inner_radius", 1),
             ("num_spikes", None), ("rotation", None)),
    "MultiLine": (("thickness", 1),),
}


def _label_cells(obj):
    """The label's COMMAND cells.

    `font_name` is deliberately absent: the reference passes a fallback list
    and the core names an asset, so comparing them would compare two spellings
    of "whatever this machine has". `content_width`/`content_height` are absent
    for a stronger reason -- they are pyglet's own text measurement, which
    docs/display-list.md puts on the shell's side of the seam. They come back
    from `metrics()` instead, because a scene whose LAYOUT reads them is a
    scene that cannot be ported without baking the number, and knowing which
    ones do is worth a separate look.
    """
    out = [
        repr(obj.text),
        _number(obj.font_size or 0.0, 1),
        str(obj.anchor_x), str(obj.anchor_y),
        # pyglet 2.1 replaced `bold` with a named weight; the reference asks
        # for bold in three places and the name is what it now stores.
        str(getattr(obj, "weight", "normal")),
    ]
    return out


def _sprite_cells(obj):
    """A sprite's command cells: scale, rotation, and the image's own size.

    The scale is divided down like a LENGTH and not left as pyglet has it.
    A sprite's scale is a ratio of drawn pixels to image pixels, so a frame
    captured at twice the reference size carries twice the scale, exactly as
    it carries twice the width of a rectangle. Leaving it alone would put one
    number of the command in pixel space while its position was in reference
    space, and a shell reading the list back would draw every sprite at the
    capture's own size.

    The image's width and height are NOT divided: they are a fact about the
    file rather than about the frame, and they are in the command because
    Reflex scales by `side / image.width` -- a core that did not know the
    width could not produce the scale.
    """
    image = obj.image
    return [
        _number(getattr(obj, "scale", 1.0), 0),
        _number(getattr(obj, "rotation", 0.0)),
        str(getattr(image, "width", 0)), str(getattr(image, "height", 0)),
    ]


def metrics():
    """Every live label's measured size, which is NOT part of a command.

    The reference reads `content_width`/`content_height` in ten places across
    seven modules. Each is a place where a layout depends on pyglet's text
    measurement, and each therefore has to be either baked as a constant --
    which is what scene_title.elisa does with a multiline label's 16.5 -- or
    left alone. This is how to find them.
    """
    out = []
    for serial, kind, ref, _extra in _LIVE:
        obj = ref()
        if obj is None or kind != "Label":
            continue
        out.append("%d|%s|%s|%s" % (
            serial, repr(obj.text),
            _number(getattr(obj, "content_width", 0.0), 0),
            _number(getattr(obj, "content_height", 0.0), 1)))
    return out


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
        elif kind == "Triangle":
            base = extra["vertices"]
            shift_x = obj.x - base[0] / 1.0
            shift_y = obj.y - base[1] / 1.0
            for at in range(2, 6, 2):
                cells.append(_number(base[at] + shift_x, 0))
                cells.append(_number(base[at + 1] + shift_y, 1))
        elif kind == "Polygon":
            for point in extra.get("coordinates", ()):
                cells.extend(_number(one, at) for at, one in enumerate(point))
        else:
            for field, axis in _FIELDS.get(kind, ()):
                cells.append(_number(getattr(obj, field, 0) or 0, axis))
            if kind == "BorderedRectangle":
                edge = tuple(obj.border_color)
                if len(edge) == 3:
                    edge = edge + (255,)
                cells.append("%d.%d.%d.%d" % edge)
            if kind == "MultiLine":
                for point in extra.get("coordinates", ()):
                    cells.extend(_number(one, at)
                                 for at, one in enumerate(point))
        rows.append((_batch_order(obj),
                     _group_order(getattr(obj, "group", None)), serial,
                     "|".join(cells)))
    _LIVE[:] = keep
    rows.sort(key=lambda row: (row[0], row[1], row[2]))
    return [row[3] for row in rows]
