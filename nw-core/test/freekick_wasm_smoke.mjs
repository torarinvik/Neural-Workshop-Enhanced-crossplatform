import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

// Free Kick through the browser ABI: the hub card, the options note (the
// reference's taskoptions.freekick_note), Space starting and then kicking,
// Enter doing neither, the eight separately held dial keys and the
// reference's order among them, key repeat, cancel, each dial turned by its
// held key, a kick set by hand landing off the ring, and then a rung-4 round
// steered key by key the way the reference's autopilot steers it -- the
// dials, the kick, the ball in the ring, the thud and the bell -- the judged
// hold, and the agent's nine ports. Every number below is the reference's
// (freekick.py driven tick for tick, 50 ms sub-stepped at 1/120 s).

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createFreeKickEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_free_kick();
assert.equal(id, 3503424810n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[2].indexOf("free_kick");
assert.equal(position, TASK_IDS_BY_CATEGORY[2].indexOf("steadicam") + 1);

const KEY = { space: 1, enter: 2, left: 3, up: 4, right: 5, down: 6, w: 77, s: 78, a: 99, d: 100 };
const EVENT = { keyDown: 2, keyUp: 3, cancel: 11 };
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
  return Number(api.nw_api_v1_free_kick_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, BigInt(flags), 0n, 0n, 0n);
}
function tick(dt = 50) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}
// The time and the dials: aim, height, curl and power, in thousandths.
function dials() {
  return [info(9), info(10), info(11), info(12), info(13)];
}
function silent(begin, end) {
  for (let from = begin; from < end; from += 1) {
    const length = api.nw_free_kick_audio_window(handle, from, Math.min(end, from + 1), pointer, capacity);
    assert.ok(length > 0n, String(length));
    if (!view(length).every(byte => byte === 0)) return false;
  }
  return true;
}

try {
  handle = api.nw_api_v1_create(id, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n);
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 2n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Free Kick"));
  const note = new TextDecoder().decode(view(api.nw_free_kick_options_note(pointer, capacity, 7n)));
  assert.equal(note, "Rung 7: a ring of 0.65 m.  A wall and a keeper.  Wind.");
  assert.ok(api.nw_free_kick_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(api.nw_free_kick_options_apply(handle, 1n, 1n, 0n), 1n);

  // Dial keys do nothing before the run starts, nor does Enter; Space starts it.
  assert.equal(dispatch(EVENT.keyDown, KEY.left), 2n);
  assert.equal(dispatch(EVENT.keyDown, KEY.enter), 2n);
  assert.equal(info(0), 0);
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  assert.equal(info(0), 1);
  const playing = texts();
  assert.ok(playing.includes("Kick it into the lit ring") && playing.includes("rung 1  1/1") &&
    ["aim", "height", "curl", "power"].every(name => playing.includes(name)), playing.join(" | "));
  assert.deepEqual(dials(), [0, 0, 12000, 0, 18000]);

  // Every dial key is its own held bit, in Left Right Up Down A D W S order.
  const bits = [[KEY.left, 1], [KEY.right, 2], [KEY.up, 4], [KEY.down, 8], [KEY.a, 16], [KEY.d, 32], [KEY.w, 64], [KEY.s, 128]];
  for (const [code, bit] of bits) {
    assert.equal(dispatch(EVENT.keyDown, code), 1n, String(code));
    assert.equal(info(14), bit);
    assert.equal(dispatch(EVENT.keyDown, code, 1), 2n, "a repeat is ignored");
    assert.equal(dispatch(EVENT.keyUp, code), 1n);
    assert.equal(info(14), 0);
  }
  assert.equal(dispatch(EVENT.keyDown, KEY.s), 1n);
  assert.equal(dispatch(EVENT.keyDown, KEY.right), 1n);
  assert.equal(info(14), 130);
  assert.equal(dispatch(EVENT.cancel), 1n);
  assert.equal(info(14), 0);

  // Left aims left, Up raises, A curls left, W kicks harder: four ticks each.
  for (const [code, after] of [[KEY.left, [200, -1200, 12000, 0, 18000]], [KEY.up, [400, -1200, 13000, 0, 18000]],
    [KEY.a, [600, -1200, 13000, 1600, 18000]], [KEY.w, [800, -1200, 13000, 1600, 19200]]]) {
    assert.equal(dispatch(EVENT.keyDown, code), 1n);
    for (let i = 0; i < 4; i++) tick();
    assert.equal(dispatch(EVENT.keyUp, code), 1n);
    assert.deepEqual(dials(), after, String(code));
  }
  // Space kicks at once; a second kick, and the dials, do nothing after it.
  assert.equal(info(15), 0);
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  assert.equal(info(15), 1);
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 2n);
  assert.equal(dispatch(EVENT.keyDown, KEY.right), 1n);
  for (let i = 0; i < 400 && info(0) === 1; i++) tick();
  assert.equal(dispatch(EVENT.keyUp, KEY.right), 1n);
  assert.equal(info(0), 2);
  assert.equal(info(8), 7, "in the goal, off the ring");
  assert.equal(now, 2600n);
  assert.deepEqual(dials(), [2557, -1200, 13000, 1600, 19200]);
  assert.equal(info(16), 1744);
  assert.equal(info(17), 0, "the ball on the goal line");
  assert.ok(texts().includes("In the goal, but 1.7 m from the ring"));
  assert.ok(silent(0, 0.79), "nothing before the kick");
  assert.ok(!silent(0.8, 1.0), "the thud of the kick");
  assert.ok(!silent(1.95, 2.3), "the growl of a miss");
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
  assert.ok(texts().some(text => text.startsWith("0 of 1 passed")));
  assert.equal(api.nw_api_v1_destroy(handle), 0n);

  // Rung 4, a wall and a keeper, steered by the reference autopilot's ports,
  // one a tick: l r u d aim and lift, L R curl, H S power, K the kick, "."
  // no key.
  handle = api.nw_api_v1_create(id, 1n, 4n, 1n, 0n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n, String(handle));
  now = 0n;
  const steering = "H13 r28 u23 K1 .34";
  const ports = steering.split(/\s+/).flatMap(run => Array(Number(run.slice(1))).fill(run[0]));
  const keyOf = { l: KEY.left, r: KEY.right, u: KEY.up, d: KEY.down, L: KEY.a, R: KEY.d, H: KEY.w, S: KEY.s, ".": 0 };
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  let held = 0;
  for (const port of ports) {
    const code = port === "K" ? 0 : keyOf[port];
    if (code !== held) {
      if (held) assert.equal(dispatch(EVENT.keyUp, held), 1n);
      if (code) assert.equal(dispatch(EVENT.keyDown, code), 1n);
      held = code;
    }
    if (port === "K") assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
    tick();
  }
  assert.equal(info(0), 2);
  assert.equal(info(8), 1, "in the ring");
  assert.equal(now, 4950n);
  assert.deepEqual(dials(), [4925, 8400, 17750, 0, 21900]);
  assert.ok(texts().includes("In the ring"));
  assert.ok(silent(0, 3.19), "nothing before the kick at 3.2 s");
  assert.ok(!silent(3.2, 3.4), "the thud of the kick");
  assert.ok(silent(3.6, 4.3), "nothing in flight");
  assert.ok(!silent(4.3, 4.7), "the bell of a goal at 4.317 s");
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
const environment = createFreeKickEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 9);
  assert.ok(environment.act(8).ok, "the kick port");
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Free Kick WASM menu, options note, Space start and kick, eight held dial keys, repeat, cancel, the dials turning, "
  + "a kick off the ring, an autopilot goal bit for bit with its thud and bell, and hold");
