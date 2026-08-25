#!/usr/bin/env python3
"""Rendering the nw-core display list with pyglet.

The Python twin of shells/web/display-list.js. That file interprets the stream
on a 2D canvas; this one interprets the same stream with pyglet shapes, labels
and sprites -- the toolkit the ORIGINAL app draws with, which is what makes
this shell the one that can be diffed against it pixel for pixel.

Two layers, deliberately:

  plan()   turns a decoded display list into a list of DrawOp records in WINDOW
           coordinates. Pure Python, no pyglet, no GL context, no display. This
           is where the reference-space mapping, letterboxing and anchor rules
           live, so they can be tested headlessly.

  Renderer feeds those ops to a factory that builds real pyglet objects into a
           Batch. The factory is injectable, so a test can record what pyglet
           would have been asked to build without opening a window.

Decoding is NOT reimplemented here: test/display_decode.py is the reference
decoder and this module imports it, exactly as display-list.js keeps its
decoder line-comparable with that file.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, NamedTuple, Optional, Sequence, Tuple

_TEST_DIR = Path(__file__).resolve().parents[2] / "test"
if str(_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(_TEST_DIR))

from display_decode import ANCHOR_NAMES, decode, rgba  # noqa: E402,F401  (re-exported)

# The historic reference space every command is expressed in. Shells own the
# mapping to physical pixels; see docs/display-list.md.
REFERENCE_WIDTH = 912.0
REFERENCE_HEIGHT = 684.0

# The original caps font size before handing it to pyglet: past this the glyphs
# stop fitting pyglet's texture atlas and the failure surfaces inside label
# creation rather than at the window size that caused it. Same number as
# neural_workshop/geometry.py's MAX_FONT_SIZE, and the same reason.
MAX_FONT_SIZE = 200.0

# Verdict codes, matching matching.elisa's verdict_code.
VERDICT_NAMES = ["correct", "incorrect", "missed", "unknown"]

# The display list's anchor names -> pyglet's. `bottom` becomes `baseline`
# rather than `bottom` on purpose: the web shell maps it to canvas's
# "alphabetic" baseline, and pyglet's `bottom` is the descender line, which
# would sit the text a few pixels lower than the browser puts it.
_ANCHOR_X = {"left": "left", "center": "center", "right": "right"}
_ANCHOR_Y = {"bottom": "baseline", "center": "center", "top": "top"}


class Viewport:
    """The reference space -> window mapping: uniform scale plus letterbox.

    `width` and `height` are the size you will DRAW in: `window.width` and
    `window.height`. On a HiDPI display pyglet 2.1 reports those in PHYSICAL
    PIXELS -- a 912x684-point window on a 2x screen reports 1824x1368, and
    `get_framebuffer_size()` agrees -- so drawing straight into that space
    fills the framebuffer at native resolution with nothing to correct. That is
    the opposite bookkeeping from the canvas shell, which gets CSS pixels and
    has to multiply by devicePixelRatio itself.

    `pixel_ratio` is pyglet's own DPI scale (`window.scale`), carried for the
    two things that still need it: converting to or from points (mouse
    coordinates, or comparing a screenshot with the browser's CSS-pixel one),
    and knowing how large a physical pixel is when judging hairlines.

    The scale is uniform and the remainder is split evenly, so a window of any
    aspect ratio shows the whole 912x684 field centred, with bars rather than
    distortion. Note this differs from the original app, which scales x by the
    width ratio and y by the height ratio independently; the display list's
    contract puts that choice in the shell, and both this shell and the web one
    choose to letterbox.
    """

    __slots__ = ("width", "height", "pixel_ratio", "scale", "offset_x", "offset_y")

    def __init__(self, width: float, height: float, pixel_ratio: float = 1.0) -> None:
        self.width = float(width)
        self.height = float(height)
        self.pixel_ratio = float(pixel_ratio)
        self.scale = min(self.width / REFERENCE_WIDTH, self.height / REFERENCE_HEIGHT)
        self.offset_x = (self.width - REFERENCE_WIDTH * self.scale) / 2.0
        self.offset_y = (self.height - REFERENCE_HEIGHT * self.scale) / 2.0

    @classmethod
    def from_window(cls, window: Any) -> "Viewport":
        """A viewport for a pyglet window, in the window's own coordinates."""
        ratio = getattr(window, "scale", None)
        if not ratio:
            # Older pyglet, or a stub in a test: derive it, and settle for 1.0
            # rather than guessing when even that is unavailable.
            try:
                framebuffer_width, _height = window.get_framebuffer_size()
                ratio = framebuffer_width / window.width if window.width else 1.0
            except Exception:
                ratio = 1.0
        return cls(window.width, window.height, ratio)

    def point(self, x: float, y: float) -> Tuple[float, float]:
        """A reference-space point in window coordinates.

        No y flip: reference space and pyglet both put the origin bottom-left
        with y up. The web shell needs one only because canvas is y-down.
        """
        return (self.offset_x + x * self.scale, self.offset_y + y * self.scale)

    def length(self, value: float) -> float:
        """A reference-space length (width, radius, thickness) in window units."""
        return value * self.scale

    def font_size(self, size: float) -> float:
        """A reference font size in pyglet points.

        Scaled, not converted: the original's labels are pyglet Labels whose
        `font_size` is this number scaled by the window ratio (geometry.py's
        calc_fontsize), so the display list carries pyglet points and the right
        thing to do is scale them. The web shell's `${size}px` is the
        approximation, on that side of the fence.
        """
        return min(MAX_FONT_SIZE, size * self.scale)

    def __repr__(self) -> str:                                    # pragma: no cover
        return (f"Viewport({self.width:g}x{self.height:g} scale={self.scale:.4f} "
                f"offset=({self.offset_x:.1f},{self.offset_y:.1f}) dpr={self.pixel_ratio:g})")


class DrawOp(NamedTuple):
    """One primitive to build, already in window coordinates."""
    kind: str
    fields: Dict[str, Any]


class Frame(NamedTuple):
    """A planned frame: what to draw, plus the non-drawing commands."""
    ops: List[DrawOp]
    verdict: Optional[int]
    sounds: List[Tuple[int, float]]
    markers: List[str]

    @property
    def verdict_name(self) -> str:
        if self.verdict is None or not 0 <= self.verdict < len(VERDICT_NAMES):
            return "none"
        return VERDICT_NAMES[self.verdict]


def plan(commands: Sequence[Mapping[str, Any]], viewport: Viewport,
         assets: Optional[Mapping[int, Any]] = None) -> Frame:
    """Map a decoded display list onto window-space draw ops.

    `assets` is consulted only to SKIP sprites whose image the shell has not
    loaded, mirroring the web shell. Pass None to plan them regardless, which
    is what a test that has no images wants.
    """
    ops: List[DrawOp] = []
    verdict: Optional[int] = None
    sounds: List[Tuple[int, float]] = []
    markers: List[str] = []

    # A polygon is a header command followed by exactly `points` PolyPoint
    # records. Points are gathered here and the polygon is emitted once the
    # last one arrives, so an incomplete run at the end of a list draws nothing
    # rather than a half polygon.
    polygon_color: Optional[int] = None
    polygon_remaining = 0
    polygon_points: List[Tuple[float, float]] = []

    for cmd in commands:
        kind = cmd["kind"]

        if kind == "rect":
            x, y = viewport.point(cmd["x"], cmd["y"])
            ops.append(DrawOp("rect", {
                "x": x, "y": y,
                "width": viewport.length(cmd["w"]), "height": viewport.length(cmd["h"]),
                "color": rgba(cmd["color"]),
            }))

        elif kind == "bordered_rect":
            x, y = viewport.point(cmd["x"], cmd["y"])
            ops.append(DrawOp("bordered_rect", {
                "x": x, "y": y,
                "width": viewport.length(cmd["w"]), "height": viewport.length(cmd["h"]),
                "border": viewport.length(cmd["border_width"]),
                "color": rgba(cmd["color"]),
                "border_color": rgba(cmd["border"]),
            }))

        elif kind == "box":
            x, y = viewport.point(cmd["x"], cmd["y"])
            ops.append(DrawOp("box", {
                "x": x, "y": y,
                "width": viewport.length(cmd["w"]), "height": viewport.length(cmd["h"]),
                "thickness": viewport.length(cmd["thickness"]),
                "color": rgba(cmd["color"]),
            }))

        elif kind == "circle":
            x, y = viewport.point(cmd["x"], cmd["y"])
            ops.append(DrawOp("circle", {
                "x": x, "y": y,
                "radius": viewport.length(cmd["radius"]),
                "color": rgba(cmd["color"]),
            }))

        elif kind == "arc":
            x, y = viewport.point(cmd["x"], cmd["y"])
            # Degrees on both sides: the display list carries degrees and
            # pyglet's Arc takes degrees too, so unlike the canvas shell (which
            # converts to radians) there is nothing to convert.
            ops.append(DrawOp("arc", {
                "x": x, "y": y,
                "radius": viewport.length(cmd["radius"]),
                "start_angle": cmd["start_angle"], "angle": cmd["sweep"],
                "color": rgba(cmd["color"]),
            }))

        elif kind == "line":
            x, y = viewport.point(cmd["x1"], cmd["y1"])
            x2, y2 = viewport.point(cmd["x2"], cmd["y2"])
            ops.append(DrawOp("line", {
                "x": x, "y": y, "x2": x2, "y2": y2,
                "thickness": viewport.length(cmd["width"]),
                "color": rgba(cmd["color"]),
            }))

        elif kind == "triangle":
            x, y = viewport.point(cmd["x1"], cmd["y1"])
            x2, y2 = viewport.point(cmd["x2"], cmd["y2"])
            x3, y3 = viewport.point(cmd["x3"], cmd["y3"])
            ops.append(DrawOp("triangle", {
                "x": x, "y": y, "x2": x2, "y2": y2, "x3": x3, "y3": y3,
                "color": rgba(cmd["color"]),
            }))

        elif kind == "polygon":
            polygon_color = cmd["color"]
            polygon_remaining = cmd["points"]
            polygon_points = []
            if polygon_remaining <= 0:          # a zero-point polygon draws nothing
                polygon_color = None

        elif kind == "poly_point":
            if polygon_color is not None:
                polygon_points.append(viewport.point(cmd["x"], cmd["y"]))
                polygon_remaining -= 1
                if polygon_remaining <= 0:
                    ops.append(DrawOp("polygon", {
                        "coordinates": polygon_points,
                        "color": rgba(polygon_color),
                    }))
                    polygon_color = None
                    polygon_points = []

        elif kind == "sprite":
            asset = cmd["asset"]
            if assets is None or asset in assets:
                x, y = viewport.point(cmd["x"], cmd["y"])
                ops.append(DrawOp("sprite", {
                    "asset": asset, "x": x, "y": y,
                    "scale": cmd["scale"] * viewport.scale,
                    # Reference space is y-up, so a positive rotation is
                    # counter-clockwise; pyglet's Sprite.rotation is clockwise.
                    "rotation": -cmd["rotation"],
                    "color": rgba(cmd["color"]),
                }))

        elif kind == "text":
            x, y = viewport.point(cmd["x"], cmd["y"])
            anchor = cmd.get("anchor", "left_bottom")
            anchor_x, _, anchor_y = anchor.partition("_")
            ops.append(DrawOp("text", {
                "text": cmd["text"], "x": x, "y": y,
                "font_size": viewport.font_size(cmd["size"]),
                "color": rgba(cmd["color"]),
                "anchor_x": _ANCHOR_X.get(anchor_x, "left"),
                "anchor_y": _ANCHOR_Y.get(anchor_y, "baseline"),
            }))

        elif kind == "verdict":
            verdict = cmd["verdict"]

        elif kind == "sound":
            sounds.append((cmd["asset"], cmd["gain"]))

        elif kind == "marker":
            markers.append(cmd["text"])

        # Anything else is a command tag this shell predates. Skipping it is
        # the documented behaviour: new commands are additive, and a shell that
        # does not understand one must step over it rather than fail.

    return Frame(ops, verdict, sounds, markers)


class PygletFactory:
    """Builds real pyglet objects from draw ops.

    pyglet is imported lazily and the three modules it needs are constructor
    arguments, so importing this file costs nothing and a test can hand in
    recording stubs instead of the real thing.
    """

    def __init__(self, shapes: Any = None, text: Any = None, sprite: Any = None,
                 batch_factory: Optional[Callable[[], Any]] = None,
                 assets: Optional[Mapping[int, Any]] = None,
                 font_name: Optional[str] = None) -> None:
        if shapes is None or text is None or sprite is None or batch_factory is None:
            import pyglet                                          # noqa: PLC0415
            shapes = shapes or pyglet.shapes
            text = text or pyglet.text
            sprite = sprite or pyglet.sprite
            batch_factory = batch_factory or pyglet.graphics.Batch
        self.shapes = shapes
        self.text = text
        self.sprite = sprite
        self.batch_factory = batch_factory
        self.assets: Mapping[int, Any] = assets or {}
        self.font_name = font_name

    def new_batch(self) -> Any:
        return self.batch_factory()

    def build(self, op: DrawOp, batch: Any) -> Any:
        """One draw op -> one pyglet object, or None if it cannot be built."""
        handler = getattr(self, "_build_" + op.kind, None)
        if handler is None:
            return None
        return handler(batch, **op.fields)

    # -- primitives ---------------------------------------------------------

    def _build_rect(self, batch, x, y, width, height, color):
        return self.shapes.Rectangle(x, y, width, height, color=color, batch=batch)

    def _build_bordered_rect(self, batch, x, y, width, height, border, color, border_color):
        # pyglet refuses a bordered rectangle whose fill and border alphas
        # differ (the blend would be ambiguous). When they do differ, the
        # border goes in as RGB, which pyglet reads as opaque -- the fill's
        # alpha is the one the display list is actually using for the shape.
        if color[3] != border_color[3]:
            border_color = border_color[:3]
        return self.shapes.BorderedRectangle(
            x, y, width, height, border=border,
            color=color, border_color=border_color, batch=batch)

    def _build_box(self, batch, x, y, width, height, thickness, color):
        return self.shapes.Box(x, y, width, height, thickness=thickness,
                               color=color, batch=batch)

    def _build_circle(self, batch, x, y, radius, color):
        return self.shapes.Circle(x, y, radius, color=color, batch=batch)

    def _build_arc(self, batch, x, y, radius, start_angle, angle, color):
        return self.shapes.Arc(x, y, radius, start_angle=start_angle, angle=angle,
                               color=color, batch=batch)

    def _build_line(self, batch, x, y, x2, y2, thickness, color):
        return self.shapes.Line(x, y, x2, y2, thickness=thickness,
                                color=color, batch=batch)

    def _build_triangle(self, batch, x, y, x2, y2, x3, y3, color):
        return self.shapes.Triangle(x, y, x2, y2, x3, y3, color=color, batch=batch)

    def _build_polygon(self, batch, coordinates, color):
        return self.shapes.Polygon(*coordinates, color=color, batch=batch)

    def _build_sprite(self, batch, asset, x, y, scale, rotation, color):
        image = self.assets.get(asset)
        if image is None:
            return None
        # The display list positions a sprite by its CENTRE, as the web shell
        # does when it draws the image at -width/2, -height/2.
        image.anchor_x = image.width // 2
        image.anchor_y = image.height // 2
        drawable = self.sprite.Sprite(image, x=x, y=y, batch=batch)
        drawable.scale = scale
        drawable.rotation = rotation
        drawable.color = color[:3]
        drawable.opacity = color[3]
        return drawable

    def _build_text(self, batch, text, x, y, font_size, color, anchor_x, anchor_y):
        return self.text.Label(text, x=x, y=y, font_size=font_size, color=color,
                               anchor_x=anchor_x, anchor_y=anchor_y,
                               font_name=self.font_name, batch=batch)


class Renderer:
    """Holds one frame's worth of pyglet objects and draws them.

    A frame is rebuilt from scratch each time rather than diffed against the
    last one. That is the honest reading of the contract -- the core emits a
    complete list every tick -- and it keeps this shell simple enough to be
    obviously correct, which is what it is for. The drawables are kept in a
    list because a pyglet shape that goes out of scope takes its vertices out
    of the batch with it.
    """

    def __init__(self, viewport: Viewport, factory: Optional[PygletFactory] = None,
                 assets: Optional[Mapping[int, Any]] = None,
                 font_name: Optional[str] = None) -> None:
        self.viewport = viewport
        self.assets: Mapping[int, Any] = assets or {}
        self.factory = factory or PygletFactory(assets=self.assets, font_name=font_name)
        self.batch = self.factory.new_batch()
        self.drawables: List[Any] = []
        self.frame: Optional[Frame] = None

    def resize(self, width: float, height: float, pixel_ratio: float = 1.0) -> None:
        self.viewport = Viewport(width, height, pixel_ratio)

    def render(self, commands: Sequence[Mapping[str, Any]]) -> Frame:
        """Plan `commands` and build the pyglet objects for them."""
        frame = plan(commands, self.viewport, self.assets or None)
        self.drawables = []
        self.batch = self.factory.new_batch()
        for op in frame.ops:
            drawable = self.factory.build(op, self.batch)
            if drawable is not None:
                self.drawables.append(drawable)
        self.frame = frame
        return frame

    def render_bytes(self, blob: bytes) -> Frame:
        """Decode an encoded display list and render it."""
        return self.render(decode(blob))

    def draw(self) -> None:
        self.batch.draw()
