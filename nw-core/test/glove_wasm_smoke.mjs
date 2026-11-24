import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

// Glove through the browser ABI: the hub card, the options note (the
// reference's taskoptions.glove_note), Space starting and Enter not, the
// eight separately held keys and the reference's order among them, key
// repeat, cancel, the glove moved by Up and by Right, then by the mouse
// through the lens the screen draws with, two pitches let by and the growls
// of the misses; then a rung-4 inning caught key by key the way the
// reference's autopilot catches it, with the thud of every catch, and the
// agent's four ports. Every number below is the reference's (glove.py driven
// tick for tick, 50 ms sub-stepped at 1/120 s).

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createGloveEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_glove();
assert.equal(id, 4083731742n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[2].indexOf("glove");
assert.equal(position, TASK_IDS_BY_CATEGORY[2].indexOf("free_kick") + 1);

const KEY = { space: 1, enter: 2, left: 3, up: 4, right: 5, down: 6, w: 77, s: 78, a: 99, d: 100 };
const EVENT = { keyDown: 2, keyUp: 3, pointerMove: 4, pointerDown: 5, cancel: 11 };
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let handle = 0n;
let now = 0n;
let sequence = 0n;

function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function texts() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)))
    .filter(command => command.text !== undefined).map(command => command.text);
}
function info(field) {
  return Number(api.nw_api_v1_glove_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, BigInt(flags), 0n, 0n, 0n);
}
function point(kind, x, y) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, 0n, 0n, 0n, 0n, BigInt(x), BigInt(y), 0n);
}
function tick(dt = 50) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}
// The time, the glove in millimetres, the view, caught, missed and the next pitch.
function at() {
  return [info(9), info(10), info(11), info(12), info(13), info(14), info(16)];
}
function silent(begin, end) {
  for (let from = begin; from < end; from += 1) {
    const length = api.nw_glove_audio_window(handle, from, Math.min(end, from + 1), pointer, capacity);
    assert.ok(length > 0n, String(length));
    if (!view(length).every(byte => byte === 0)) return false;
  }
  return true;
}

try {
  handle = api.nw_api_v1_create(id, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n);
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 2n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Glove"));
  const note = new TextDecoder().decode(view(api.nw_glove_options_note(pointer, capacity, 7n)));
  assert.equal(note, "Rung 7: 5 pitches at 23 m/s.  A cut about every 0.8 s.");
  assert.ok(api.nw_glove_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(api.nw_glove_options_apply(handle, 1n, 1n, 0n), 1n);

  // Keys do nothing before the inning starts, nor does Enter; Space starts it.
  // A move of the pointer before then is where the next one is measured from.
  assert.equal(point(EVENT.pointerMove, 500000, 500000), 2n);
  assert.equal(dispatch(EVENT.keyDown, KEY.up), 2n);
  assert.equal(dispatch(EVENT.keyDown, KEY.enter), 2n);
  assert.equal(info(0), 0);
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  assert.equal(info(0), 1);
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 2n, "Space does nothing in play");
  const playing = texts();
  assert.ok(playing.includes("Catch the pitches") && playing.includes("rung 1  1/1   pitch 1 of 4") &&
    playing.includes("caught 0   missed 0"), playing.join(" | "));
  assert.deepEqual(at(), [0, 0, 1150, 0, 0, 0, 0]);

  // Every key is its own held bit: Up W Down S Left A Right D.
  const bits = [[KEY.up, 1], [KEY.w, 2], [KEY.down, 4], [KEY.s, 8], [KEY.left, 16], [KEY.a, 32], [KEY.right, 64], [KEY.d, 128]];
  for (const [code, bit] of bits) {
    assert.equal(dispatch(EVENT.keyDown, code), 1n, String(code));
    assert.equal(info(15), bit);
    assert.equal(dispatch(EVENT.keyDown, code, 1), 2n, "a repeat is ignored");
    assert.equal(dispatch(EVENT.keyUp, code), 1n);
    assert.equal(info(15), 0);
  }
  assert.equal(dispatch(EVENT.keyDown, KEY.d), 1n);
  assert.equal(dispatch(EVENT.keyDown, KEY.s), 1n);
  assert.equal(info(15), 136);
  assert.equal(dispatch(EVENT.cancel), 1n);
  assert.equal(info(15), 0);

  // Up and Right four ticks each, Up winning over Right while both are held.
  assert.equal(dispatch(EVENT.keyDown, KEY.right), 1n);
  assert.equal(dispatch(EVENT.keyDown, KEY.w), 1n);
  for (let i = 0; i < 4; i++) tick();
  assert.equal(dispatch(EVENT.keyUp, KEY.w), 1n);
  assert.deepEqual(at(), [200, 0, 1670, 0, 0, 0, 0]);
  for (let i = 0; i < 4; i++) tick();
  assert.equal(dispatch(EVENT.keyUp, KEY.right), 1n);
  assert.deepEqual(at(), [400, -520, 1670, 0, 0, 0, 0]);
  // The mouse, 22.8 px left and 17.1 px down from where it was before the start.
  assert.equal(point(EVENT.pointerMove, 475000, 475000), 1n);
  assert.deepEqual(at(), [400, -320, 1520, 0, 0, 0, 0]);
  for (let i = 0; i < 400 && info(0) === 1; i++) tick();
  assert.equal(info(0), 2);
  assert.equal(info(8), 2, "missed");
  assert.equal(now, 6850n);
  assert.deepEqual(at(), [6833, -320, 1520, 0, 0, 2, 2]);
  assert.ok(texts().includes("Missed 2"));
  assert.ok(silent(0, 3.3), "nothing before the first miss");
  assert.ok(!silent(3.33, 3.6), "the growl of the first miss");
  assert.ok(!silent(6.83, 7.1), "the growl of the second");
  assert.equal(point(EVENT.pointerMove, 400000, 400000), 2n, "the glove stays put once judged");
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
  assert.ok(texts().some(text => text.startsWith("0 of 1 passed")));
  assert.equal(api.nw_api_v1_destroy(handle), 0n);

  // Rung 4, steered by the reference autopilot's ports, one a tick: u d l r
  // up, down, left and right, "." no key.
  handle = api.nw_api_v1_create(id, 1n, 4n, 1n, 0n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n, String(handle));
  now = 0n;
  const steering = fs.readFileSync(new URL("./fixtures/glove_pilot_rung4_seed17.txt", import.meta.url), "utf8").trim();
  const ports = steering.split(/\s+/).flatMap(run => Array(Number(run.slice(1))).fill(run[0]));
  const keyOf = { u: KEY.up, d: KEY.down, l: KEY.left, r: KEY.right, ".": 0 };
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  let held = 0;
  for (const port of ports) {
    const code = keyOf[port];
    if (code !== held) {
      if (held) assert.equal(dispatch(EVENT.keyUp, held), 1n);
      if (code) assert.equal(dispatch(EVENT.keyDown, code), 1n);
      held = code;
    }
    tick();
  }
  assert.equal(info(0), 2);
  assert.equal(info(8), 1, "caught");
  assert.equal(now, 14600n);
  assert.deepEqual(at(), [14600, 539, 741, 3, 5, 0, 5]);
  assert.ok(texts().includes("Caught 5 of 5"));
  assert.ok(silent(0, 2.9), "nothing before the first catch at 2.95 s");
  for (const t of [2.95, 5.7333, 8.5833, 11.9333]) assert.ok(!silent(t, t + 0.15), `the thud of a catch at ${t} s`);
  assert.ok(silent(3.3, 5.7), "nothing between the first two catches");
} finally {
  if (handle) api.nw_api_v1_destroy(handle);
  api.nw_frame_free(pointer);
}

const canvas = { width: 228, height: 171 };
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, moveTo() {}, lineTo() {}, closePath() {},
  clearRect() {}, fillRect() {}, fillText() {},
  getImageData: () => ({ data: new Uint8ClampedArray(canvas.width * canvas.height * 4) }),
};
const environment = createGloveEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 4);
  assert.ok(environment.act(0).ok, "the up port");
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Glove WASM menu, options note, Space start, eight held keys, repeat, cancel, the glove moved by keys and "
  + "by the mouse through the lens, an inning let by with its growls, an autopilot inning caught bit for bit with its "
  + "thuds, and hold");
