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
