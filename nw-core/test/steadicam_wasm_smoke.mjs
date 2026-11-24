import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

// Steadicam through the browser ABI: the hub card, the options note (the
// reference's taskoptions.steadicam_note), Space and only Space starting,
// the ten separately held camera keys and the reference's order among them,
// key repeat, cancel, a primary-button drag panning and tilting by the
// pixel, the wheel zooming, a walker lost for three seconds, and then a
// rung-13 take steered key by key the way the reference's autopilot steers
// it -- whom to follow changing on the park's cues, the bell on each, the
// verdict and the camera where the reference leaves them -- the judged
// hold, and the agent's six ports. Every number below is the reference's
// (steadicam.py driven tick for tick, 50 ms sub-stepped at 1/120 s).

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createSteadicamEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_steadicam();
assert.equal(id, 2305084378n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[2].indexOf("steadicam");
assert.equal(position, TASK_IDS_BY_CATEGORY[2].indexOf("kerbside") + 1);

const KEY = { space: 1, enter: 2, left: 3, up: 4, right: 5, down: 6, w: 77, s: 78, a: 99, d: 100, q: 101, e: 102 };
const EVENT = { keyDown: 2, keyUp: 3, pointerMove: 4, pointerDown: 5, pointerUp: 6, wheel: 7, cancel: 11 };
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
  return Number(api.nw_api_v1_steadicam_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, BigInt(flags), 0n, 0n, 0n);
}
function point(kind, x, y, button = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(button), 0n, 0n, 0n, BigInt(x), BigInt(y), 0n);
}
function wheel(deltaY) {
  return api.nw_api_v1_dispatch(handle, BigInt(EVENT.wheel), now, sequence++, 0n, BigInt(deltaY * 1000), 0n, 0n, 500000n, 500000n, 0n);
}
function tick(dt = 50) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}
function camera() {
  return [info(9), info(10), info(11), info(12)];
}
// Whether the run's sound over [begin, end) is all zero, a second at most
// a window as the audio export allows.
function silent(begin, end) {
  for (let from = begin; from < end; from += 1) {
    const length = api.nw_steadicam_audio_window(handle, from, Math.min(end, from + 1), pointer, capacity);
    assert.ok(length > 0n, String(length));
    if (!view(length).every(byte => byte === 0)) return false;
  }
  return true;
}

try {
  handle = api.nw_api_v1_create(id, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n);
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 2n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Steadicam"));
  const note = new TextDecoder().decode(view(api.nw_steadicam_options_note(pointer, capacity, 10n)));
  assert.equal(note, "Rung 10: 35 s, 80% framed.  A heavy head.  Leave lead room.");
  assert.ok(api.nw_steadicam_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(api.nw_steadicam_options_apply(handle, 1n, 1n, 0n), 1n);

  // Camera keys do nothing before the take starts, nor does Enter; Space starts it.
  assert.equal(dispatch(EVENT.keyDown, KEY.right), 2n);
  assert.equal(dispatch(EVENT.keyDown, KEY.enter), 2n);
  assert.equal(info(0), 0);
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  assert.equal(info(0), 1);
  const playing = texts();
  assert.ok(playing.includes("Keep the walker in the box") && playing.some(text => text.startsWith("rung 1  1/1   framed 0% (need 80%)")),
    playing.join(" | "));
  assert.deepEqual(camera(), [0, 646, -25, 873]);

  // Every key is its own held bit, in Left A Right D Up W Down S E Q order.
  const bits = [[KEY.left, 1], [KEY.a, 2], [KEY.right, 4], [KEY.d, 8], [KEY.up, 16], [KEY.w, 32],
    [KEY.down, 64], [KEY.s, 128], [KEY.e, 256], [KEY.q, 512]];
  for (const [code, bit] of bits) {
    assert.equal(dispatch(EVENT.keyDown, code), 1n, String(code));
    assert.equal(info(14), bit);
    assert.equal(dispatch(EVENT.keyDown, code, 1), 2n, "a repeat is ignored");
    assert.equal(dispatch(EVENT.keyUp, code), 1n);
    assert.equal(info(14), 0);
  }
  assert.equal(dispatch(EVENT.keyDown, KEY.q), 1n);
  assert.equal(dispatch(EVENT.keyDown, KEY.left), 1n);
  assert.equal(info(14), 513);
  assert.equal(dispatch(EVENT.cancel), 1n);
  assert.equal(info(14), 0);
  assert.deepEqual(camera(), [0, 646, -25, 873], "nothing moved while no time passed");

  // Right pans right, W tilts up, E zooms in -- each held for four ticks.
  for (const [code, after] of [[KEY.d, [200, 783, -25, 873]], [KEY.w, [400, 783, 112, 873]], [KEY.e, [600, 783, 112, 729]]]) {
    assert.equal(dispatch(EVENT.keyDown, code), 1n);
    for (let i = 0; i < 4; i++) tick();
    assert.equal(dispatch(EVENT.keyUp, code), 1n);
    assert.deepEqual(camera(), after, String(code));
  }
  // A drag with the primary button pans and tilts by fov / 900 a pixel; a
  // secondary button's release is not the drag's end; the wheel zooms in.
  assert.equal(point(EVENT.pointerDown, 500000, 500000), 1n);
  assert.equal(point(EVENT.pointerMove, 600000, 550000), 1n);
  assert.equal(point(EVENT.pointerUp, 600000, 550000, 2), 2n);
  assert.equal(point(EVENT.pointerUp, 600000, 550000), 1n);
  assert.equal(point(EVENT.pointerMove, 700000, 700000), 2n, "no drag after the release");
  assert.deepEqual(camera(), [600, 857, 140, 729]);
  assert.equal(wheel(-100), 1n);
  assert.deepEqual(camera(), [600, 857, 140, 673]);

  // Left like that, the walker is lost for three seconds.
  for (let i = 0; i < 400 && info(0) === 1; i++) tick();
  assert.equal(info(0), 2);
  assert.equal(info(8), 3, "lost them");
  assert.equal(now, 4050n);
  assert.deepEqual(camera(), [4008, 857, 140, 673]);
  assert.ok(texts().includes("Lost them for 3 seconds"));
  assert.ok(silent(0, 4), "one walker, no cues, no bell");
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
  assert.ok(texts().some(text => text.startsWith("0 of 1 passed")));
  assert.equal(api.nw_steadicam_audio_window(handle, 0, 1, pointer, capacity), 0n);
  assert.equal(api.nw_api_v1_destroy(handle), 0n);

  // Rung 13, two people, steered by the reference autopilot's ports, one a
  // tick, each as its key: L R U D for the pans and tilts, I and O for E
  // and Q, "." for no key.
  handle = api.nw_api_v1_create(id, 1n, 13n, 1n, 0n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n, String(handle));
  now = 0n;
  const steering = fs.readFileSync(new URL("./fixtures/steadicam_pilot_rung13_seed17.txt", import.meta.url), "utf8").trim();
  const ports = steering.split(/\s+/).flatMap(run => Array(Number(run.slice(1))).fill(run[0]));
  const keyOf = { L: KEY.left, R: KEY.right, U: KEY.up, D: KEY.down, I: KEY.e, O: KEY.q, ".": 0 };
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  assert.equal(info(17), 2);
  assert.equal(info(15), 0);
  assert.ok(texts().includes("Follow the red one"));
  const changes = [];
  let held = 0;
  let whom = info(15);
  for (let i = 0; i < ports.length; i++) {
    const code = keyOf[ports[i]];
    if (code !== held) {
      if (held) assert.equal(dispatch(EVENT.keyUp, held), 1n);
      if (code) assert.equal(dispatch(EVENT.keyDown, code), 1n);
      held = code;
    }
    tick();
    if (info(15) !== whom) { whom = info(15); changes.push([i, whom]); }
  }
  assert.deepEqual(changes, [[180, 1], [324, 0], [492, 1], [708, 0]]);
  assert.equal(info(0), 2);
  assert.equal(info(8), 1, "passed");
  assert.equal(now, 40050n);
  assert.deepEqual(camera(), [40008, 1342, -36, 439]);
  assert.equal(info(13), 97);
  assert.ok(texts().includes("Framed 97% of the time, 78% needed"));
  // The bell on each cue after the first (9.007 s, 16.214 s, ...), and
  // silence before the first.
  assert.ok(silent(0, 9.0), "silence before the first cue");
  assert.ok(!silent(9.0, 9.3), "the bell at the first cue");
  assert.ok(!silent(16.2, 16.5), "the bell at the second cue");
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
const environment = createSteadicamEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 6);
  assert.ok(environment.act(1).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Steadicam WASM menu, options note, Space start, ten held camera keys, repeat, cancel, drag, wheel, a lost walker, an autopilot take bit for bit with its cues and bells, and hold");
