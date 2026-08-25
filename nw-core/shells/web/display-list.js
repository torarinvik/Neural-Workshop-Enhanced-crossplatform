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
    VERDICT: 12, SOUND: 13, MARKER: 14,
};

const ANCHORS = [
    ["left", "bottom"], ["center", "bottom"], ["right", "bottom"],
    ["left", "middle"], ["center", "middle"], ["right", "middle"],
    ["left", "top"], ["center", "top"], ["right", "top"],
];

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

export function css(color) {
    const r = (color >>> 24) & 255, g = (color >>> 16) & 255;
    const b = (color >>> 8) & 255, a = color & 255;
    return `rgba(${r},${g},${b},${(a / 255).toFixed(3)})`;
}

// Renders into a canvas sized to any device pixel ratio. The core works in
// reference space with y UP; the canvas has y DOWN, so the transform flips
// once here rather than in every command.
export function render(ctx, commands, { width, height, assets = {} } = {}) {
    const scale = Math.min(width / REFERENCE_WIDTH, height / REFERENCE_HEIGHT);
    const offsetX = (width - REFERENCE_WIDTH * scale) / 2;
    const offsetY = (height - REFERENCE_HEIGHT * scale) / 2;

    ctx.save();
    ctx.clearRect(0, 0, width, height);
    ctx.setTransform(scale, 0, 0, -scale, offsetX, height - offsetY);

    let polygon = null;
    const events = { verdict: null, sounds: [], markers: [] };

    for (const cmd of commands) {
        switch (cmd.kind) {
            case Kind.RECT:
                ctx.fillStyle = css(cmd.color);
                ctx.fillRect(cmd.a, cmd.b, cmd.c, cmd.d);
                break;
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
                polygon = { remaining: cmd.len, color: cmd.color, started: false };
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
                        ctx.closePath();
                        ctx.fillStyle = css(polygon.color);
                        ctx.fill();
                        polygon = null;
                    }
                }
                break;
            case Kind.SPRITE: {
                const image = assets[cmd.ref];
                if (image) {
                    ctx.save();
                    ctx.translate(cmd.a, cmd.b);
                    ctx.rotate((cmd.e * Math.PI) / 180);
                    ctx.scale(cmd.c, -cmd.c); // un-flip: images are y-down
                    ctx.drawImage(image, -image.width / 2, -image.height / 2);
                    ctx.restore();
                }
                break;
            }
            case Kind.TEXT: {
                // Text must not be mirrored by the y-flip, so it draws in a
                // temporarily un-flipped frame.
                ctx.save();
                ctx.translate(cmd.a, cmd.b);
                ctx.scale(1, -1);
                ctx.fillStyle = css(cmd.color);
                ctx.font = `${cmd.c}px system-ui, sans-serif`;
                ctx.textAlign = cmd.anchor ? cmd.anchor[0] : "left";
                ctx.textBaseline = cmd.anchor
                    ? { bottom: "alphabetic", middle: "middle", top: "top" }[cmd.anchor[1]]
                    : "alphabetic";
                ctx.fillText(cmd.text, 0, 0);
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
    ctx.restore();
    return events;
}
