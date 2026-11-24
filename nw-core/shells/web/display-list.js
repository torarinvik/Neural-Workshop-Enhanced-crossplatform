// Decoding and rendering the nw-core display list on a 2D canvas.
//
// The decoder is a direct transliteration of test/display_decode.py — the two
// must agree, and keeping them line-comparable is how that stays true.

export const MAGIC = 1313426254;
export const VERSION = 1;
export const CMD_SIZE = 40;

export const REFERENCE_WIDTH = 912;
export const REFERENCE_HEIGHT = 684;

export const Kind = {
    RECT: 1, BORDERED_RECT: 2, BOX: 3, CIRCLE: 4, ARC: 5, LINE: 6,
    TRIANGLE: 7, POLYGON: 8, POLY_POINT: 9, SPRITE: 10, TEXT: 11,
    VERDICT: 12, SOUND: 13, MARKER: 14, SPRITE_FIT: 15,
    MULTILINE: 16, STAR: 17,
};

const ANCHORS = [
    ["left", "bottom"], ["center", "bottom"], ["right", "bottom"],
    ["left", "middle"], ["center", "middle"], ["right", "middle"],
    ["left", "top"], ["center", "top"], ["right", "top"],
];

const TEXT_FACES = [
    "Arial", "Times New Roman", "Courier New", "Georgia", "Impact", "Comic Sans MS",
    "Futura", "Marker Felt", "Papyrus", "Didot", "American Typewriter", "Rockwell",
    "Chalkduster", "Bradley Hand", "Copperplate", "Verdana",
];
const TEXT_FACE_FALLBACK = "Arial, Helvetica, 'DejaVu Sans', 'Liberation Sans', sans-serif";

export function decode(bytes) {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    if (bytes.byteLength < 16) throw new Error("display list: truncated header");
    const magic = view.getUint32(0, true);
    if (magic !== MAGIC) throw new Error(`display list: bad magic ${magic}`);
    const version = view.getUint32(4, true);
    if (version !== VERSION) throw new Error(`display list: version ${version} unsupported`);
    const count = view.getUint32(8, true);
    const poolLen = view.getUint32(12, true);

    const poolAt = 16 + count * CMD_SIZE;
    const pool = bytes.subarray(poolAt, poolAt + poolLen);
    const decoder = new TextDecoder();
    const commands = [];

    for (let i = 0; i < count; i++) {
        const at = 16 + i * CMD_SIZE;
        const cmd = {
            kind: view.getUint8(at),
            color: view.getUint32(at + 4, true),
            a: view.getFloat32(at + 8, true),
            b: view.getFloat32(at + 12, true),
            c: view.getFloat32(at + 16, true),
            d: view.getFloat32(at + 20, true),
            e: view.getFloat32(at + 24, true),
            f: view.getFloat32(at + 28, true),
            ref: view.getUint32(at + 32, true),
            len: view.getUint32(at + 36, true),
        };
        if (cmd.kind === Kind.TEXT || cmd.kind === Kind.MARKER) {
            const length = cmd.len & 0xffffff;
            cmd.text = decoder.decode(pool.subarray(cmd.ref, cmd.ref + length));
            if (cmd.kind === Kind.TEXT) cmd.anchor = ANCHORS[(cmd.len >>> 24) & 0xff];
        }
        commands.push(cmd);
    }
    return commands;
}

// An f32 read back out of a u32 slot -- the bytes, not the value.
const _bits = new DataView(new ArrayBuffer(4));
export function rotationOf(bits) {
    _bits.setUint32(0, bits >>> 0, true);
    return _bits.getFloat32(0, true);
}

export function css(color) {
    const r = (color >>> 24) & 255, g = (color >>> 16) & 255;
    const b = (color >>> 8) & 255, a = color & 255;
    return `rgba(${r},${g},${b},${(a / 255).toFixed(3)})`;
}

// Pyglet's Quartz glyph renderer rounds each glyph's advance to a whole
// framebuffer pixel. Canvas normally keeps fractional advances, which makes
// long fixed-width strings visibly wider. Round after the active x scale and
// convert the advances back to user coordinates for placement.
export function fillTextRoundedAdvances(ctx, text, x, y, {
    align = "left", pixelScale = 1, strokeWidth = 0,
} = {}) {
    const glyphs = Array.from(text);
    const advances = glyphs.map(glyph =>
        Math.round(ctx.measureText(glyph).width * pixelScale) / pixelScale);
    const width = advances.reduce((sum, advance) => sum + advance, 0);
    let cursor = x - (align === "center" ? width / 2 : align === "right" ? width : 0);
    if (strokeWidth > 0) {
        ctx.lineWidth = strokeWidth;
        ctx.strokeStyle = ctx.fillStyle;
    }
    for (let index = 0; index < glyphs.length; index++) {
        if (strokeWidth > 0) ctx.strokeText(glyphs[index], cursor, y);
        ctx.fillText(glyphs[index], cursor, y);
        cursor += advances[index];
    }
    return width;
}

// Renders into a canvas sized to any device pixel ratio. The core works in
// reference space with y UP; the canvas has y DOWN, so the transform flips
// once here rather than in every command.
export function render(ctx, commands, {
    width, height, assets = {}, fontFamily = "system-ui, sans-serif",
    fontScale = 1, textOffsetY = 0, roundGlyphAdvances = false,
    glyphStrokeRatio = 0, replaceRect = null, afterCommands = null, replaceFittedSprite = null,
    referenceWidth = REFERENCE_WIDTH, referenceHeight = REFERENCE_HEIGHT, sceneImage = null,
} = {}) {
    const scale = Math.min(width / referenceWidth, height / referenceHeight);
    const offsetX = (width - referenceWidth * scale) / 2;
    const offsetY = (height - referenceHeight * scale) / 2;

    ctx.save();
    // Host game layers can leave a scaled/flipped transform behind. Clearing
    // under that transform erases only part of the framebuffer, so old text
    // and geometry accumulate on every animation frame.
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, width, height);
    if (sceneImage) ctx.drawImage(sceneImage, 0, 0, width, height);
    ctx.setTransform(scale, 0, 0, -scale, offsetX, height - offsetY);

    let polygon = null;
    const events = { verdict: null, sounds: [], markers: [] };

    for (const cmd of commands) {
        switch (cmd.kind) {
            case Kind.RECT: {
                if (typeof replaceRect === "function" && replaceRect(ctx, cmd)) break;
                // `e`, `f` are the anchor inside the rectangle and `ref` holds
                // the BITS of the rotation about it. Both are zero for all but
                // two screens, so the plain path stays a single fillRect.
                const rotation = rotationOf(cmd.ref);
                ctx.fillStyle = css(cmd.color);
                if (!rotation && !cmd.e && !cmd.f) {
                    ctx.fillRect(cmd.a, cmd.b, cmd.c, cmd.d);
                    break;
                }
                ctx.save();
                ctx.translate(cmd.a, cmd.b);
                // Same sign as the sprite branch below, so one file has one
                // convention. See docs/display-list.md: what the core stores is
                // pyglet's own `rotation`, and no screen yet draws a rotated
                // sprite, so nothing has pinned the sign across shells.
                ctx.rotate((rotation * Math.PI) / 180);
                ctx.fillRect(-cmd.e, -cmd.f, cmd.c, cmd.d);
                ctx.restore();
                break;
            }
            case Kind.BORDERED_RECT:
                ctx.fillStyle = css(cmd.color);
                ctx.fillRect(cmd.a, cmd.b, cmd.c, cmd.d);
                ctx.strokeStyle = css(cmd.ref);
                ctx.lineWidth = cmd.e;
                ctx.strokeRect(cmd.a, cmd.b, cmd.c, cmd.d);
                break;
            case Kind.BOX:
                ctx.strokeStyle = css(cmd.color);
                ctx.lineWidth = cmd.e;
                ctx.strokeRect(cmd.a, cmd.b, cmd.c, cmd.d);
                break;
            case Kind.CIRCLE:
                ctx.fillStyle = css(cmd.color);
                ctx.beginPath();
                ctx.arc(cmd.a, cmd.b, cmd.c, 0, Math.PI * 2);
                ctx.fill();
                break;
            case Kind.ARC:
                ctx.strokeStyle = css(cmd.color);
                ctx.lineWidth = 1;
                ctx.beginPath();
                ctx.arc(cmd.a, cmd.b, cmd.c, (cmd.e * Math.PI) / 180,
                        ((cmd.e + cmd.f) * Math.PI) / 180);
                ctx.stroke();
                break;
            case Kind.LINE:
                ctx.strokeStyle = css(cmd.color);
                ctx.lineWidth = cmd.e;
                ctx.beginPath();
                ctx.moveTo(cmd.a, cmd.b);
                ctx.lineTo(cmd.c, cmd.d);
                ctx.stroke();
                break;
            case Kind.TRIANGLE:
                ctx.fillStyle = css(cmd.color);
                ctx.beginPath();
                ctx.moveTo(cmd.a, cmd.b);
                ctx.lineTo(cmd.c, cmd.d);
                ctx.lineTo(cmd.e, cmd.f);
                ctx.closePath();
                ctx.fill();
                break;
            case Kind.POLYGON:
                polygon = { remaining: cmd.len, color: cmd.color, started: false,
                            stroke: false };
                break;
            case Kind.MULTILINE:
                // The same header-and-points shape as a polygon, drawn as an
                // OPEN stroked run rather than a closed fill.
                polygon = { remaining: cmd.len, color: cmd.color, started: false,
                            stroke: true, thickness: cmd.c };
                break;
            case Kind.POLY_POINT:
                if (polygon) {
                    if (!polygon.started) {
                        ctx.beginPath();
                        ctx.moveTo(cmd.a, cmd.b);
                        polygon.started = true;
                    } else {
                        ctx.lineTo(cmd.a, cmd.b);
                    }
                    if (--polygon.remaining <= 0) {
                        if (polygon.stroke) {
                            ctx.strokeStyle = css(polygon.color);
                            ctx.lineWidth = polygon.thickness;
                            ctx.stroke();
                        } else {
                            ctx.closePath();
                            ctx.fillStyle = css(polygon.color);
                            ctx.fill();
                        }
                        polygon = null;
                    }
                }
                break;
            case Kind.STAR: {
                // `spikes` points alternating between the outer and the inner
                // radius, the first one at `rotation` degrees from straight up
                // -- pyglet's Star, whose first point is at the top.
                const spikes = Math.max(2, Math.round(cmd.e));
                ctx.fillStyle = css(cmd.color);
                ctx.beginPath();
                for (let step = 0; step < spikes * 2; step++) {
                    const radius = step % 2 === 0 ? cmd.c : cmd.d;
                    const turn = (cmd.f * Math.PI) / 180
                               + (step * Math.PI) / spikes;
                    const px = cmd.a + radius * Math.sin(turn);
                    const py = cmd.b + radius * Math.cos(turn);
                    if (step === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
                }
                ctx.closePath();
                ctx.fill();
                break;
            }
            case Kind.SPRITE: {
                const image = assets[cmd.ref];
                if (image) {
                    // CMD_SPRITE stores pyglet's bottom-left origin, not its
                    // centre. Keep the rotation centre at the sprite's visual
                    // centre while preserving that wire-level origin. (The
                    // separate SPRITE_FIT command stores a room centre.)
                    const drawWidth = image.width * cmd.c;
                    const drawHeight = image.height * cmd.c;
                    ctx.save();
                    ctx.translate(cmd.a + drawWidth / 2,
                                  cmd.b + drawHeight / 2);
                    ctx.rotate((cmd.e * Math.PI) / 180);
                    ctx.scale(cmd.c, -cmd.c); // un-flip: images are y-down
                    ctx.drawImage(image, -image.width / 2, -image.height / 2);
                    ctx.restore();
                }
                break;
            }
            case Kind.SPRITE_FIT: {
                if (typeof replaceFittedSprite === "function" && replaceFittedSprite(ctx, cmd)) break;
                // The core names a room; the shell owns the fit, because only
                // the shell has decoded the image and knows its size. Same rule
                // as bootstrap._place_splash: keep the aspect, land inside.
                const image = assets[cmd.ref];
                if (image) {
                    const scale = Math.min(cmd.c / image.width, cmd.d / image.height);
                    ctx.save();
                    ctx.translate(cmd.a, cmd.b);
                    ctx.rotate((cmd.e * Math.PI) / 180);
                    ctx.scale(scale, -scale); // un-flip: images are y-down
                    ctx.drawImage(image, -image.width / 2, -image.height / 2);
                    ctx.restore();
                }
                break;
            }
            case Kind.TEXT: {
                // Text must not be mirrored by the y-flip, so it draws in a
                // temporarily un-flipped frame.
                ctx.save();
                ctx.fillStyle = css(cmd.color);
                const commandTextOffsetY = typeof textOffsetY === "function"
                    ? textOffsetY(cmd) : textOffsetY;
                const face = TEXT_FACES[cmd.f - 1];
                const family = face ? `"${face}", ${TEXT_FACE_FALLBACK}` : fontFamily;
                // `d` is the weight: every task screen's title asks for bold,
                // and a title back at normal weight is a different frame.
                if (roundGlyphAdvances && !face && !cmd.e) {
                    const align = cmd.anchor ? cmd.anchor[0] : "left";
                    ctx.setTransform(1, 0, 0, 1, 0, 0);
                    ctx.font = `${cmd.d ? "bold " : ""}${cmd.c * fontScale * scale}px ${family}`;
                    ctx.textAlign = "left";
                    ctx.textBaseline = cmd.anchor
                        ? { bottom: "alphabetic", middle: "middle", top: "top" }[cmd.anchor[1]]
                        : "alphabetic";
                    const x = offsetX + cmd.a * scale;
                    const y = height - offsetY - (cmd.b + commandTextOffsetY) * scale;
                    const lines = cmd.text.split("\n");
                    lines.forEach((line, index) => fillTextRoundedAdvances(ctx, line, x,
                        y + (index - (lines.length - 1) / 2) * cmd.c * fontScale * scale * 1.25, {
                            align, pixelScale: 1,
                            strokeWidth: cmd.c * fontScale * scale * glyphStrokeRatio,
                        }));
                } else {
                    ctx.translate(cmd.a, cmd.b + commandTextOffsetY);
                    ctx.scale(1, -1);
                    if (cmd.e) ctx.rotate(cmd.e * Math.PI / 180);
                    ctx.font = `${cmd.d ? "bold " : ""}${cmd.c * fontScale}px ${family}`;
                    ctx.textAlign = cmd.anchor ? cmd.anchor[0] : "left";
                    ctx.textBaseline = cmd.anchor
                        ? { bottom: "alphabetic", middle: "middle", top: "top" }[cmd.anchor[1]]
                        : "alphabetic";
                    const lines = cmd.text.split("\n");
                    lines.forEach((line, index) => ctx.fillText(line, 0,
                        (index - (lines.length - 1) / 2) * cmd.c * fontScale * 1.25));
                }
                ctx.restore();
                break;
            }
            case Kind.VERDICT:
                events.verdict = cmd.ref;
                break;
            case Kind.SOUND:
                events.sounds.push({ asset: cmd.ref, gain: cmd.a });
                break;
            case Kind.MARKER:
                events.markers.push(cmd.text);
                break;
        }
    }
    if (typeof afterCommands === "function") {
        afterCommands(ctx, { scale, offsetX, offsetY, width, height });
    }
    ctx.restore();
    return events;
}
