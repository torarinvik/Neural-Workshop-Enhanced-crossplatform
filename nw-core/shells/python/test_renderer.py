#!/usr/bin/env python3
"""Headless checks for the pyglet shell.

    python3 shells/python/test_renderer.py

No window, no GL context, no pyglet import: the renderer's mapping layer is
pure Python, and the pyglet layer is exercised through recording stubs that
stand in for pyglet.shapes/text/sprite. What is asserted is exactly what a
display would otherwise have to be trusted to show -- which pyglet class gets
built for each command, and with which numbers.

The last check is the cross-shell one: the same bytes are handed to the JS
decoder in shells/web/display-list.js through node, and the two decoders must
produce the same commands. Two shells that disagree about the wire format is
the failure this port most needs to catch early, and it cannot be caught from
inside either shell alone.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import types
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]                        # nw-core/
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from renderer import (MAX_FONT_SIZE, PygletFactory, REFERENCE_HEIGHT,  # noqa: E402
                      REFERENCE_WIDTH, Renderer, Viewport, decode, plan)
from display_decode import canonical  # noqa: E402

# The representative frame: every command kind, in the shape test/display_diff.py
# already pins. Produced by build/display_sweep_stage0 (test/display_sweep.elisa)
# and embedded so this test needs neither a build nor a compiler; the first
# check below re-runs that binary when it is present and fails if it has drifted.
FRAME_HEX = (
    "4e4b494e010000001a0000002300000001000000ff00000000000000000000000000644400002b4400000000000000000000"
    "00000000000003000000ff404040000099430000e44200009643000096430000004000000000000000000000000002000000"
    "ffff80000000cb43000056430000c8420000c8420000404000000000ffffffff0000000004000000ff00c8ff0000e4430000"
    "84430000c041000000000000000000000000000000000000000005000000ff8080800000e443000084430000204200000000"
    "0000000000003443000000000000000006000000ff5a5a5a000000000000c842000064440000c8420000c03f000000000000"
    "00000000000007000000ffff00ff00002041000020410000f041000020410000a0410000f041000000000000000008000000"
    "ff0ac80a0000c8420000c84200000000000000000000000000000000000000000300000009000000000000000000c8420000"
    "c842000000000000000000000000000000000000000000000000090000000000000000000c430000c8420000000000000000"
    "0000000000000000000000000000000009000000000000000000f04200000c43000000000000000000000000000000000000"
    "0000000000000a000000ffffffff00002f440000fa430000c03f000080420000b4420000404207000000000000000b000000"
    "ffffffff0000e4430000704200009041000000000000000000000000000000000e0000040b000000ffc8c8c80000a0410080"
    "2244000060410000000000000000000000000e000000050000060b000000ff00ffff0000e44300001b44000040410000803f"
    "0000000000000000130000000700000701000000ff0302010000484300009643000020420000a0410000a041000020410000"
    "00000000000001000000ff06050400007a430000a043000020420000a0410000a041000020410000f041000000000f000000"
    "ffffffff000048440000c8430000f0420000b4420000344200000000090000000000000011000000ff0080ff0000fa430000"
    "c8430000f041000040410000a04000009041000000000000000010000000ffffff0000007042000070420000204000000000"
    "0000000000000000000000000300000009000000000000000000704200007042000000000000000000000000000000000000"
    "00000000000009000000000000000000a0420000b44200000000000000000000000000000000000000000000000009000000"
    "000000000000dc4200008c420000000000000000000000000000000000000000000000000d00000000000000cdcc4c3f0000"
    "00000000000000000000000000000000000003000000000000000c0000000000000000000000000000000000000000000000"
    "000000000000000000000000000000000e000000000000000000000000000000000000000000000000000000000000001a00"
    "000009000000506f736974696f6e206d617463684e203d2032547269616c2034747269616c2d656e64"
)
FRAME = bytes.fromhex(FRAME_HEX)

WEB_DECODER = _ROOT / "shells" / "web" / "display-list.js"
SWEEP_BINARY = _ROOT / "build" / "display_sweep_stage0"

failures: list[str] = []


def check(condition: bool, label: str, detail: str = "") -> None:
    if condition:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label}" + (f"\n       {detail}" if detail else ""))
        failures.append(label)


def close(a: float, b: float, tolerance: float = 1e-4) -> bool:
    return abs(a - b) <= tolerance


# ---------------------------------------------------------------- the fixture

def test_fixture_matches_the_sweep() -> None:
    """The embedded frame is the one the Elisa encoder actually produces."""
    if not SWEEP_BINARY.exists():
        print(f"  skip embedded frame vs {SWEEP_BINARY.name} (not built)")
        return
    hex_text = subprocess.run([str(SWEEP_BINARY)], capture_output=True, text=True,
                              check=True).stdout.strip()
    check(bytes.fromhex(hex_text) == FRAME, "embedded frame matches display_sweep",
          "rebuild the constant from build/display_sweep_stage0")


# ------------------------------------------------------------------- viewport

def test_viewport() -> None:
    exact = Viewport(REFERENCE_WIDTH, REFERENCE_HEIGHT)
    check(exact.scale == 1.0 and exact.offset_x == 0 and exact.offset_y == 0,
          "reference-sized window maps 1:1", repr(exact))
    check(exact.point(0.0, 0.0) == (0.0, 0.0) and exact.point(912.0, 684.0) == (912.0, 684.0),
          "corners map to corners with no y flip")

    doubled = Viewport(1824, 1368)
    check(doubled.scale == 2.0 and doubled.point(10, 20) == (20.0, 40.0),
          "uniform scale, origin still bottom-left")

    wide = Viewport(1824, 684)                  # twice as wide as it needs to be
    check(wide.scale == 1.0 and close(wide.offset_x, 456.0) and wide.offset_y == 0.0,
          "a too-wide window letterboxes horizontally", repr(wide))
    tall = Viewport(912, 1368)
    check(tall.scale == 1.0 and tall.offset_x == 0.0 and close(tall.offset_y, 342.0),
          "a too-tall window letterboxes vertically", repr(tall))
    check(close(wide.point(0, 0)[0], 456.0) and close(tall.point(0, 0)[1], 342.0),
          "the letterbox offset moves the field, not just the maths")

    # HiDPI: pyglet 2.1 reports window.width in PHYSICAL PIXELS, so a 912-point
    # window on a 2x screen is 1824 wide and the field scales up to fill it --
    # no devicePixelRatio multiply of our own, unlike the canvas shell. The
    # ratio is recorded for callers that need to get back to points.
    window = types.SimpleNamespace(width=1824, height=1368, scale=2.0,
                                   get_framebuffer_size=lambda: (1824, 1368))
    hidpi = Viewport.from_window(window)
    check(hidpi.scale == 2.0 and hidpi.pixel_ratio == 2.0,
          "HiDPI window: drawn at native resolution, ratio recorded", repr(hidpi))
    legacy = types.SimpleNamespace(width=912, height=684,
                                   get_framebuffer_size=lambda: (1824, 1368))
    check(Viewport.from_window(legacy).pixel_ratio == 2.0,
          "without window.scale the ratio comes from the framebuffer size")

    check(close(exact.font_size(22.0), 22.0) and close(Viewport(456, 342).font_size(22.0), 11.0),
          "font size scales with the viewport")
    check(Viewport(200000, 150000).font_size(22.0) == MAX_FONT_SIZE,
          "font size is capped where pyglet's atlas gives out")


# ----------------------------------------------------------------- planning

def test_plan_kinds_and_events() -> None:
    frame = plan(decode(FRAME), Viewport(REFERENCE_WIDTH, REFERENCE_HEIGHT))
    kinds = [op.kind for op in frame.ops]
    expected = ["rect", "box", "bordered_rect", "circle", "arc", "line",
                "triangle", "polygon", "sprite", "text", "text", "text",
                "rect", "rect", "sprite_fit", "star", "multiline"]
    check(kinds == expected, "every drawing command becomes one op",
          f"{kinds} != {expected}")
    check(frame.verdict == 0 and frame.verdict_name == "correct",
          "verdict is lifted out of the draw ops", repr(frame.verdict))
    check(len(frame.sounds) == 1 and frame.sounds[0][0] == 3
          and close(frame.sounds[0][1], 0.8), "sound event carried", repr(frame.sounds))
    check(frame.markers == ["trial-end"], "marker carried", repr(frame.markers))


def _by_kind(frame):
    """First op of each kind. The frame now holds three rectangles -- plain,
    anchored and turned -- and a dict keyed by kind would silently keep only
    the last."""
    out = {}
    for op in frame.ops:
        out.setdefault(op.kind, op.fields)
    return out


def _all_of(frame, kind):
    return [op.fields for op in frame.ops if op.kind == kind]


def test_plan_geometry() -> None:
    frame = plan(decode(FRAME), Viewport(REFERENCE_WIDTH, REFERENCE_HEIGHT))
    ops = _by_kind(frame)

    rect = ops["rect"]
    check(rect["x"] == 0 and rect["y"] == 0 and rect["width"] == 912
          and rect["height"] == 684 and rect["color"] == (0, 0, 0, 255),
          "rect: position, size and RGBA", repr(rect))

    box = ops["box"]
    check(box["x"] == 306 and box["y"] == 114 and box["thickness"] == 2.0,
          "box: outline thickness kept separate from size", repr(box))

    bordered = ops["bordered_rect"]
    check(bordered["color"] == (0, 128, 255, 255)
          and bordered["border_color"] == (255, 255, 255, 255)
          and bordered["border"] == 3.0,
          "bordered_rect: fill and border are different colours", repr(bordered))

    arc = ops["arc"]
    check(close(arc["radius"], 40.0) and arc["start_angle"] == 0.0 and arc["angle"] == 180.0,
          "arc: degrees pass through, as pyglet wants them", repr(arc))

    line = ops["line"]
    check(line["x"] == 0 and line["x2"] == 912 and close(line["thickness"], 1.5),
          "line: endpoints and thickness", repr(line))

    triangle = ops["triangle"]
    check((triangle["x"], triangle["y"], triangle["x2"], triangle["y2"],
           triangle["x3"], triangle["y3"]) == (10, 10, 30, 10, 20, 30),
          "triangle: three corners in order", repr(triangle))

    polygon = ops["polygon"]
    check(polygon["coordinates"] == [(100.0, 100.0), (140.0, 100.0), (120.0, 140.0)],
          "polygon: header count gathers exactly its points", repr(polygon))

    sprite = ops["sprite"]
    check(sprite["asset"] == 7 and close(sprite["scale"], 1.5)
          and close(sprite["rotation"], -90.0),
          "sprite: rotation negated for pyglet's clockwise convention", repr(sprite))

    # The three rectangles differ only in their last three slots, which is the
    # point: a shell that ignored them would draw all three identically.
    plain, anchored, turned = _all_of(frame, "rect")
    check(plain["anchor_x"] == 0 and plain["anchor_y"] == 0
          and plain["rotation"] == 0.0,
          "rect: an ordinary rectangle carries no anchor and no angle",
          repr(plain))
    check(anchored["anchor_x"] == 20.0 and anchored["anchor_y"] == 10.0
          and anchored["rotation"] == 0.0,
          "rect: an anchored rectangle keeps its anchor", repr(anchored))
    check(close(turned["rotation"], 30.0) and turned["anchor_x"] == 20.0,
          "rect: the angle survives the u32 slot it rides in", repr(turned))

    star = ops["star"]
    check(close(star["outer_radius"], 30.0) and close(star["inner_radius"], 12.0)
          and star["num_spikes"] == 5 and close(star["rotation"], 18.0),
          "star: both radii, the spike count and the angle", repr(star))

    multi = ops["multiline"]
    check(multi["coordinates"] == [(60.0, 60.0), (80.0, 90.0), (110.0, 70.0)]
          and close(multi["thickness"], 2.5),
          "multiline: an open run of points with its own thickness", repr(multi))

    fitted = ops["sprite_fit"]
    check(close(fitted["room_w"], 120.0) and close(fitted["room_h"], 90.0),
          "sprite_fit: the room, not a scale", repr(fitted))


def test_plan_text_anchors() -> None:
    texts = [op.fields for op in
             plan(decode(FRAME), Viewport(REFERENCE_WIDTH, REFERENCE_HEIGHT)).ops
             if op.kind == "text"]
    first, second, third = texts
    check(third["text"] == "Trial 4" and third["bold"] is True
          and second["bold"] is False,
          "the weight slot separates a bold label from a plain one",
          repr(third))
    check(first["text"] == "Position match" and first["anchor_x"] == "center"
          and first["anchor_y"] == "center" and close(first["font_size"], 18.0),
          "centred label keeps its anchor", repr(first))
    check(second["text"] == "N = 2" and second["anchor_x"] == "left"
          and second["anchor_y"] == "top" and second["color"] == (200, 200, 200, 255),
          "top-left label keeps its anchor", repr(second))

    # `bottom` becomes pyglet's `baseline`, matching the canvas shell's
    # "alphabetic" -- pyglet's own `bottom` is the descender line and would sit
    # the glyphs lower than the browser puts them.
    bottom = [op.fields for op in
              plan([{"kind": "text", "text": "x", "x": 0.0, "y": 0.0, "size": 10.0,
                     "color": 0xFFFFFFFF, "anchor": "left_bottom"}],
                   Viewport(REFERENCE_WIDTH, REFERENCE_HEIGHT)).ops][0]
    check(bottom["anchor_y"] == "baseline", "bottom anchor becomes baseline",
          repr(bottom))


def test_plan_scaling() -> None:
    """Everything a command carries has to move with the viewport."""
    frame = plan(decode(FRAME), Viewport(456, 342))          # half size
    ops = _by_kind(frame)
    check(ops["rect"]["width"] == 456 and ops["rect"]["height"] == 342,
          "lengths halve with the viewport", repr(ops["rect"]))
    check(close(ops["line"]["thickness"], 0.75) and close(ops["box"]["thickness"], 1.0),
          "thicknesses halve too -- a hairline stays a hairline",
          repr(ops["line"]))
    check(close(ops["arc"]["radius"], 20.0) and ops["arc"]["angle"] == 180.0,
          "radii scale, angles do not", repr(ops["arc"]))
    check(close([op.fields for op in frame.ops if op.kind == "text"][0]["font_size"], 9.0),
          "font size scales")
    # A rectangle's anchor is a length inside it, so it halves; its angle is an
    # angle, so it does not.
    turned = _all_of(frame, "rect")[2]
    check(close(turned["anchor_x"], 10.0) and close(turned["rotation"], 30.0),
          "a rectangle's anchor scales and its angle does not", repr(turned))
    check(close(_by_kind(frame)["star"]["outer_radius"], 15.0)
          and close(_by_kind(frame)["multiline"]["thickness"], 1.25),
          "a star's radii and a multiline's thickness scale too")


def test_plan_edge_cases() -> None:
    viewport = Viewport(REFERENCE_WIDTH, REFERENCE_HEIGHT)

    truncated = [{"kind": "polygon", "points": 3, "color": 0xFF0000FF},
                 {"kind": "poly_point", "x": 0.0, "y": 0.0},
                 {"kind": "poly_point", "x": 1.0, "y": 0.0}]
    check(plan(truncated, viewport).ops == [],
          "a polygon missing its last point draws nothing")

    orphan = [{"kind": "poly_point", "x": 0.0, "y": 0.0}]
    check(plan(orphan, viewport).ops == [], "a point with no polygon draws nothing")

    unknown = [{"kind": "unknown_99"}, {"kind": "rect", "x": 0.0, "y": 0.0,
                                        "w": 1.0, "h": 1.0, "color": 0xFFFFFFFF}]
    check([op.kind for op in plan(unknown, viewport).ops] == ["rect"],
          "an unknown command tag is stepped over, not fatal")

    # `assets` is the shell saying which images it actually holds.
    sprite = [{"kind": "sprite", "asset": 7, "x": 0.0, "y": 0.0, "scale": 1.0,
               "rotation": 0.0, "color": 0xFFFFFFFF}]
    check(len(plan(sprite, viewport).ops) == 1, "sprite planned when assets unknown")
    check(plan(sprite, viewport, assets={}).ops == [],
          "sprite skipped when the shell has no image for it")


# ------------------------------------------------------- the pyglet layer

def _recording_pyglet():
    """Stand-ins for pyglet.shapes / pyglet.text / pyglet.sprite.

    Each fake constructor records its name and arguments and returns an object
    that accepts attribute assignment, which is how Sprite is configured.
    """
    log: list[tuple[str, tuple, dict]] = []

    def module(*names):
        namespace = types.SimpleNamespace()
        for name in names:
            def make(name):
                def constructor(*args, **kwargs):
                    log.append((name, args, kwargs))
                    return types.SimpleNamespace(name=name, args=args, kwargs=kwargs)
                return constructor
            setattr(namespace, name, make(name))
        return namespace

    shapes = module("Rectangle", "BorderedRectangle", "Box", "Circle", "Arc",
                    "Line", "Triangle", "Polygon", "MultiLine", "Star")
    text = module("Label")
    sprite = module("Sprite")
    batches = []

    def batch_factory():
        batch = types.SimpleNamespace(draw=lambda: batches.append("draw"))
        return batch

    return log, batches, shapes, text, sprite, batch_factory


def test_pyglet_classes() -> None:
    log, batches, shapes, text, sprite, batch_factory = _recording_pyglet()
    image = types.SimpleNamespace(width=32, height=32)
    factory = PygletFactory(shapes=shapes, text=text, sprite=sprite,
                            batch_factory=batch_factory, assets={7: image})
    renderer = Renderer(Viewport(REFERENCE_WIDTH, REFERENCE_HEIGHT), factory=factory,
                        assets={7: image})
    frame = renderer.render(decode(FRAME))

    built = [name for name, _args, _kwargs in log]
    expected = ["Rectangle", "Box", "BorderedRectangle", "Circle", "Arc", "Line",
                "Triangle", "Polygon", "Sprite", "Label", "Label", "Label",
                "Rectangle", "Rectangle", "Star", "MultiLine"]
    # No second Sprite: the fitted one names asset 9 and this factory holds
    # only 7, so it plans and then declines to build -- which is the rule for
    # an image the shell has not loaded.
    check(built == expected, "each command builds its pyglet class",
          f"{built} != {expected}")
    check(len(renderer.drawables) == len(expected),
          "every drawable is held: a shape that is collected leaves the batch",
          f"{len(renderer.drawables)}")

    # FIRST of each name: the frame builds three rectangles and three labels,
    # and a last-wins dict would check the turned rectangle where the plain one
    # is meant.
    by_name = {}
    for name, args, kwargs in log:
        by_name.setdefault(name, (args, kwargs))

    args, kwargs = by_name["Rectangle"]
    check(args == (0.0, 0.0, 912.0, 684.0) and kwargs["color"] == (0, 0, 0, 255)
          and kwargs["batch"] is renderer.batch,
          "Rectangle(x, y, w, h, color=..., batch=...)", repr((args, kwargs)))

    args, kwargs = by_name["Arc"]
    check(kwargs["start_angle"] == 0.0 and kwargs["angle"] == 180.0,
          "Arc takes start_angle/angle in degrees", repr(kwargs))

    args, kwargs = by_name["Line"]
    check(close(kwargs["thickness"], 1.5),
          "Line takes `thickness`, the pyglet 2.1 name", repr(kwargs))

    args, kwargs = by_name["Polygon"]
    check(args == ((100.0, 100.0), (140.0, 100.0), (120.0, 140.0)),
          "Polygon takes its points as positional coordinates", repr(args))

    labels = [(args, kwargs) for name, args, kwargs in log if name == "Label"]
    check([(k["anchor_x"], k["anchor_y"]) for _a, k in labels]
          == [("center", "center"), ("left", "top"), ("center", "top")],
          "each Label carries its own anchor pair", repr(labels))
    check([k["weight"] for _a, k in labels] == ["normal", "normal", "bold"],
          "the weight reaches pyglet as a named weight, not a `bold` flag",
          repr([k["weight"] for _a, k in labels]))
    check(labels[0][0] == ("Position match",) and close(labels[0][1]["font_size"], 18.0),
          "Label(text, font_size=...) in pyglet points", repr(labels[0]))

    check(image.anchor_x == 16 and image.anchor_y == 16,
          "a sprite image is anchored at its centre, as the web shell draws it")
    built_sprite = [d for d in renderer.drawables if getattr(d, "name", "") == "Sprite"][0]
    check(close(built_sprite.scale, 1.5) and close(built_sprite.rotation, -90.0)
          and built_sprite.color == (255, 255, 255) and built_sprite.opacity == 255,
          "sprite scale/rotation/colour set after construction",
          repr(built_sprite))

    renderer.draw()
    check(batches == ["draw"], "draw() draws the batch, once")
    check(frame.verdict == 0, "the frame's verdict survives rendering")


def test_bordered_rect_alpha_rule() -> None:
    """pyglet refuses a bordered rectangle whose two alphas disagree."""
    log, _batches, shapes, text, sprite, batch_factory = _recording_pyglet()
    factory = PygletFactory(shapes=shapes, text=text, sprite=sprite,
                            batch_factory=batch_factory)
    batch = factory.new_batch()
    commands = [{"kind": "bordered_rect", "x": 0.0, "y": 0.0, "w": 10.0, "h": 10.0,
                 "color": 0x0080FF80, "border": 0xFFFFFFFF, "border_width": 2.0}]
    op = plan(commands, Viewport(REFERENCE_WIDTH, REFERENCE_HEIGHT)).ops[0]
    factory.build(op, batch)
    _name, _args, kwargs = log[0]
    check(kwargs["color"] == (0, 128, 255, 128) and kwargs["border_color"] == (255, 255, 255),
          "mismatched alphas: the border goes in as RGB rather than raising",
          repr(kwargs))


# ------------------------------------------------------- decoder agreement

JS_PROBE = r"""
import { decode, Kind, rotationOf } from %(module)s;

const KIND_NAMES = Object.fromEntries(
    Object.entries(Kind).map(([name, value]) => [value, name.toLowerCase()]));

const rgba = (c) => [(c >>> 24) & 255, (c >>> 16) & 255, (c >>> 8) & 255, c & 255].join(":");
const f = (v) => v.toFixed(4);

// The same slot naming test/display_decode.py's _fill applies, so the two
// decoders can be compared on one canonical line per command. What is being
// checked is the DECODING -- magic, version, offsets, endianness, the string
// pool, the packed anchor -- not this table.
function fields(c) {
    const k = c.kind, out = {};
    if (k === Kind.RECT || k === Kind.BORDERED_RECT || k === Kind.BOX) {
        Object.assign(out, { x: f(c.a), y: f(c.b), w: f(c.c), h: f(c.d), color: rgba(c.color) });
        if (k === Kind.RECT) Object.assign(out, { anchor_x: f(c.e), anchor_y: f(c.f), rotation: f(rotationOf(c.ref)) });
        if (k === Kind.BORDERED_RECT) Object.assign(out, { border: rgba(c.ref), border_width: f(c.e) });
        if (k === Kind.BOX) out.thickness = f(c.e);
    } else if (k === Kind.CIRCLE) {
        Object.assign(out, { x: f(c.a), y: f(c.b), radius: f(c.c), color: rgba(c.color) });
    } else if (k === Kind.ARC) {
        Object.assign(out, { x: f(c.a), y: f(c.b), radius: f(c.c), start_angle: f(c.e), sweep: f(c.f), color: rgba(c.color) });
    } else if (k === Kind.LINE) {
        Object.assign(out, { x1: f(c.a), y1: f(c.b), x2: f(c.c), y2: f(c.d), width: f(c.e), color: rgba(c.color) });
    } else if (k === Kind.TRIANGLE) {
        Object.assign(out, { x1: f(c.a), y1: f(c.b), x2: f(c.c), y2: f(c.d), x3: f(c.e), y3: f(c.f), color: rgba(c.color) });
    } else if (k === Kind.POLYGON) {
        Object.assign(out, { points: String(c.len), color: rgba(c.color) });
    } else if (k === Kind.POLY_POINT) {
        Object.assign(out, { x: f(c.a), y: f(c.b) });
    } else if (k === Kind.SPRITE) {
        Object.assign(out, { asset: String(c.ref), x: f(c.a), y: f(c.b), scale: f(c.c), rotation: f(c.e), color: rgba(c.color),
                             image_w: String(Math.trunc(c.d)), image_h: String(Math.trunc(c.f)) });
    } else if (k === Kind.SPRITE_FIT) {
        Object.assign(out, { asset: String(c.ref), x: f(c.a), y: f(c.b), room_w: f(c.c), room_h: f(c.d), rotation: f(c.e), color: rgba(c.color) });
    } else if (k === Kind.MULTILINE) {
        Object.assign(out, { x: f(c.a), y: f(c.b), thickness: f(c.c), points: String(c.len), color: rgba(c.color) });
    } else if (k === Kind.STAR) {
        Object.assign(out, { x: f(c.a), y: f(c.b), outer: f(c.c), inner: f(c.d), spikes: String(Math.trunc(c.e)), rotation: f(c.f), color: rgba(c.color) });
    } else if (k === Kind.TEXT) {
        const anchor = c.anchor[0] + "_" + (c.anchor[1] === "middle" ? "center" : c.anchor[1]);
        Object.assign(out, { x: f(c.a), y: f(c.b), size: f(c.c), color: rgba(c.color), text: c.text, anchor,
                             bold: c.d ? "True" : "False" });
    } else if (k === Kind.VERDICT) {
        out.verdict = String(c.ref);
    } else if (k === Kind.SOUND) {
        Object.assign(out, { asset: String(c.ref), gain: f(c.a) });
    } else if (k === Kind.MARKER) {
        out.text = c.text;
    }
    return out;
}

const bytes = Uint8Array.from(Buffer.from(process.argv[2], "hex"));
const lines = decode(bytes).map((c) => {
    const named = fields(c);
    const parts = [KIND_NAMES[c.kind]];
    for (const key of Object.keys(named).sort()) parts.push(key + "=" + named[key]);
    return parts.join(" ");
});
process.stdout.write(JSON.stringify(lines));
"""


def js_canonical(blob: bytes) -> list:
    module = json.dumps(WEB_DECODER.as_uri())
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as handle:
        handle.write(JS_PROBE % {"module": module})
        script = handle.name
    try:
        result = subprocess.run(["node", script, blob.hex()],
                                capture_output=True, text=True, check=True)
    finally:
        os.unlink(script)
    return json.loads(result.stdout)


def test_decoders_agree() -> None:
    if not WEB_DECODER.exists():
        print("  skip decoder agreement (shells/web/display-list.js missing)")
        return
    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        print("  skip decoder agreement (no node)")
        return

    blobs = [("display_sweep frame", FRAME)]

    # A live core frame too when the extension is built: the sweep frame is a
    # fixture, and a fixture cannot notice the encoder changing under it.
    core = _load_core()
    if core is not None:
        blobs.append(("nwcore.title_frame(1, 0, 1, 1)", core.title_frame(1, 0, 1, 1)))
        blobs.append(("nwcore.title_frame(2, 0, 1, 1)", core.title_frame(2, 0, 1, 1)))

    for label, blob in blobs:
        mine = canonical(decode(blob))
        theirs = js_canonical(blob)
        if mine == theirs:
            check(True, f"python and js decoders agree on {label} "
                        f"({len(mine)} commands)")
            continue
        detail = "\n       ".join(
            f"[{i}]\n         py: {a}\n         js: {b}"
            for i, (a, b) in enumerate(zip(mine, theirs)) if a != b) or \
            f"lengths {len(mine)} vs {len(theirs)}"
        check(False, f"python and js decoders agree on {label}", detail)


# --------------------------------------------------------- the live core

def _load_core():
    pymod = _ROOT / "build" / "pymod"
    if str(pymod) not in sys.path:
        sys.path.insert(0, str(pymod))
    try:
        import nwcore                                              # noqa: PLC0415
    except ImportError:
        return None
    return nwcore if hasattr(nwcore, "title_frame") else None


def test_core_frames() -> None:
    core = _load_core()
    if core is None:
        print("  skip live core (run scripts/build_pymodule.sh)")
        return

    blob = core.title_frame(1, 0, 1, 1)
    check(isinstance(blob, bytes) and len(blob) > 16,
          "title_frame returns bytes", repr(type(blob)))

    frame = plan(decode(blob), Viewport(REFERENCE_WIDTH, REFERENCE_HEIGHT))
    kinds = [op.kind for op in frame.ops]
    check(kinds.count("rect") == 1 and kinds.count("sprite_fit") == 1,
          "title frame contains its background and splash", repr(kinds))
    texts = [op.fields["text"] for op in frame.ops if op.kind == "text"]
    check("Press SPACE to enter the Workshop" in texts
          and "F11: Full Screen" in texts
          and all("N-Back" not in text for text in texts),
          "the port title contains no generic mode affordance", repr(texts))
    check(frame.markers == ["frame-end"],
          "title marker comes through", repr(frame))

    # The wasm build returns stale darray storage from the second call onward
    # (repro/nw_wasm32_darray_second_call.elisa). Native must not: if this ever
    # fails, the bug is not wasm-specific after all.
    repeats = {core.title_frame(1, 0, 1, 1) for _ in range(64)}
    check(repeats == {blob}, "64 repeat calls return identical bytes",
          f"{len(repeats)} distinct results")
    varied = [core.title_frame(t % 4, 0, 1, 1) for t in range(1, 40)]
    texts = {tuple(c["text"] for c in decode(b) if "text" in c) for b in varied}
    check(all("N-Back" not in text for group in texts for text in group),
          "pooled title strings stay intact across calls", repr(texts))


def main() -> int:
    for test in (test_fixture_matches_the_sweep, test_viewport,
                 test_plan_kinds_and_events, test_plan_geometry,
                 test_plan_text_anchors, test_plan_scaling, test_plan_edge_cases,
                 test_pyglet_classes, test_bordered_rect_alpha_rule,
                 test_core_frames, test_decoders_agree):
        print(test.__name__)
        test()
    print()
    if failures:
        print(f"FAILED: {len(failures)} check(s): " + ", ".join(failures))
        return 1
    print("PASS: the pyglet shell agrees with the display list and with the web decoder")
    return 0


if __name__ == "__main__":
    sys.exit(main())
