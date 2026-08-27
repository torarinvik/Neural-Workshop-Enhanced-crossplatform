# The display list — the core's output contract

The Elisa core does not draw. Once per tick it emits a **display list**: a flat,
typed command stream describing what the frame should look like, plus audio
events and the trial's verdict. Each platform shell interprets that list with
whatever it has — pyglet, SDL3, Canvas2D, Metal.

This is the seam that makes one core serve browser, desktop and mobile, and it
is why ~32k lines of pyglet UI become a per-shell renderer instead of a port.

## Why a list and not a callback API

A retained command list is *data*. That buys three things a draw-callback API
cannot:

1. **Testability.** A frame is a value, so it can be recorded, hashed and
   diffed. The same differential method used for the kernels applies to
   rendering: capture a stream from the original game and compare.
2. **Transport.** A list can cross a process, a socket or a WASM boundary
   unchanged, so a web build can run the core server-side over a WebSocket
   before the WASM runtime port lands, and the same bytes work afterwards.
3. **A verdict channel that isn't pixels.** The original derives the agent's
   reward by counting coloured label runs in the bottom quarter of the
   rendered frame. Reproducing that across four renderers on five platforms is
   a tar pit — the original's own notes record seven tasks getting the band
   rule subtly wrong within a single renderer. Here the verdict is a
   first-class command, so verification anchors to the signed command stream
   rather than to anti-aliased pixels.

## Coordinate space

All coordinates are in the historic **912 × 684 reference space**, origin
bottom-left, y up (matching the original's geometry module). Shells own the
mapping to physical pixels — that is where HiDPI, letterboxing and
device-pixel-ratio live, solved once per platform instead of once per widget.

## Command record

One flat 40-byte record per command, so a shell can walk the stream without
allocating and a binary encoder is a memcpy:

| field | type | meaning |
|---|---|---|
| `kind` | u8 | command tag |
| `color` | u32 | RGBA, 8 bits per channel |
| `a` `b` | f32 | x, y (or x1, y1) |
| `c` `d` | f32 | w, h — or x2, y2 — or radius |
| `e` `f` | f32 | per-command extras: line width, rotation, font size, angles |
| `ref` | u32 | string offset, or an asset id (sprite, sound, mesh) |
| `len` | u32 | string length, or an asset variant |

Strings are not embedded. Each list carries a byte pool; text commands hold an
`(offset, length)` pair into it. That keeps records fixed-size and makes the
whole list two contiguous buffers.

## Commands

Drawing primitives are exactly the set the original UI uses, in the proportions
it uses them (258 labels, 64 rectangles, 49 circles, 42 lines, 13 polygons, 10
sprites, 9 bordered rectangles, 8 boxes, 6 arcs, 3 triangles):

`Rect` · `BorderedRect` · `Box` · `Circle` · `Arc` · `Line` · `Triangle` ·
`Polygon` (points follow as `PolyPoint` records) · `Sprite` · `Text`

Five later additions, each of them additive — a shell written before one of
them either skips the tag or reads a zero where the new field is, and a zero is
what it drew anyway:

- **`SpriteFit`** — a sprite given a ROOM rather than a scale. Only the shell
  has decoded the image, so only the shell can fit it.
- **`MultiLine`** — the same header-and-`PolyPoint` shape as `Polygon`, drawn
  as an open stroked run. `c` is the thickness; `a`, `b` repeat the first
  point, because that is where pyglet puts the run's own origin.
- **`Star`** — `c` outer radius, `d` inner, `e` spike count, `f` the angle of
  the first point from straight up.
- **`Rect`'s anchor and angle** — `e`, `f` are the anchor inside the rectangle
  and `ref` carries the BITS of an f32 angle about it. Two screens use them
  (a Lookout glyph, a Tetris piece in the air); every other rectangle leaves
  all three at zero.
- **`Text`'s weight** — `d` is 1 for bold. Every task screen's title asks for
  bold, and a title back at normal weight is a different frame.

`Sprite` also carries the decoded image's own pixel size in `d` and `f`. It is
there because some screens scale BY it — Reflex sizes a target by
`side / image.width` — so a core that did not know the width could not produce
the scale. It is a fact about the FILE, not about the frame, so a shell must
not rescale it with the viewport.

**Rotation's sign is not yet pinned across shells.** What the core stores is
pyglet's own `rotation`, which is clockwise, and that is what the differential
harness compares. The pyglet shell negates a sprite's angle and the canvas
shell does not; no screen in the workshop draws a rotated sprite, so nothing
has ever told the two apart. A shell adding rotation should follow whatever its
own sprite branch already does, and the day a rotated sprite appears, this is
the paragraph that gets deleted and replaced by a test.

Plus three non-drawing commands:

- **`Verdict`** — the trial's outcome as data. `ref` carries the verdict code
  (correct / incorrect / missed / unknown). A shell may render it however it
  likes; the agent boundary reads the command, not the pixels.
- **`Sound`** — a sound id to play. Decoding and mixing are the shell's job.
- **`Marker`** — a named frame annotation for tests and replays.

## Encoding

Two encodings, one meaning:

- **Binary**: little-endian, `[u32 magic][u32 version][u32 cmd_count][u32
  pool_len][commands…][pool bytes]`. What shells consume.
- **Canonical text**: one line per command, fields in fixed order, floats
  printed at fixed precision. What tests diff. A float that differs in the last
  bit shows up as a text difference rather than hiding inside a hash.

The version word is checked by shells. A shell that does not understand a
command tag must skip it by size rather than fail — new commands are additive.

## What stays out of the core

Font rasterisation, image decoding, audio decoding and mixing, window and input
plumbing, HiDPI scaling, and localisation *rendering*. The core emits message
keys and asset ids; shells resolve them.
