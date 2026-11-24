import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

// By Ear through the browser ABI: the hub card, the options note (the
// reference's taskoptions.byear_note), Space starting and Enter not, keys
// ignored while the tune plays, a rung-1 tune played back by the keys the
// reference's autopilot presses -- the tune, each key and the bell of the
// verdict where the reference's come -- then a shifted rung-10 tune played
// back by clicks on the keys, its first key lit gold once it has played, and
// a rung-13 pair let fall apart; and the agent's thirteen ports. Every
// number below is the reference's (byear.py driven tick for tick, 50 ms
// sub-stepped at 1/120 s, the keys where ByEar._keys puts them).

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createByEarEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_by_ear();
assert.equal(id, 2841258479n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[3].indexOf("by_ear");
assert.equal(position, TASK_IDS_BY_CATEGORY[3].indexOf("captcha") + 1);

// Space, Enter, and the keys from C to C: A W S E D F T G Y H U J K.
const KEY = { space: 1, enter: 2, first: 103 };
const EVENT = { keyDown: 2, keyUp: 3, pointerDown: 5 };
// ByEar._keys at 912 x 684: each key's x, y, width and height.
const RECTS = {
  0: [70.224, 237.35, 96.444, 272.3], 2: [166.668, 237.35, 96.444, 272.3], 4: [263.112, 237.35, 96.444, 272.3],
  5: [359.556, 237.35, 96.444, 272.3], 7: [456.0, 237.35, 96.444, 272.3], 9: [552.444, 237.35, 96.444, 272.3],
  11: [648.888, 237.35, 96.444, 272.3], 12: [745.332, 237.35, 96.444, 272.3], 1: [137.735, 340.824, 57.866, 168.826],
  3: [234.179, 340.824, 57.866, 168.826], 6: [427.067, 340.824, 57.866, 168.826], 8: [523.511, 340.824, 57.866, 168.826],
  10: [619.955, 340.824, 57.866, 168.826],
};
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let handle = 0n;
let now = 0n;
let sequence = 0n;

function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function frame() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)));
}
function texts() {
  return frame().filter(command => command.text !== undefined).map(command => command.text);
}
function info(field) {
  return Number(api.nw_api_v1_by_ear_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, BigInt(flags), 0n, 0n, 0n);
}
function press(key) {
  return dispatch(EVENT.keyDown, KEY.first + key);
}
// A primary click at reference pixels (x, y) from the bottom left.
function click(x, y) {
  return api.nw_api_v1_dispatch(handle, BigInt(EVENT.pointerDown), now, sequence++, 0n, 0n, 0n, 0n,
    BigInt(Math.round(x * 1000000 / 912)), BigInt(Math.round(y * 1000000 / 684)), 0n);
}
// The middle of a key's part that nothing covers.
function clickKey(key) {
  const [x, y, w, h] = RECTS[key];
  return click(x + w / 2, key in { 1: 1, 3: 1, 6: 1, 8: 1, 10: 1 } ? y + h / 2 : y + 40);
}
function tick(dt = 50) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}
function until(ms) {
  while (now < BigInt(ms)) tick();
}
function silent(begin, end) {
  for (let from = begin; from < end; from += 1) {
    const length = api.nw_by_ear_audio_window(handle, from, Math.min(end, from + 1), pointer, capacity);
    assert.ok(length > 0n, String(length));
    if (!view(length).every(byte => byte === 0)) return false;
  }
  return true;
}
// Inner key rectangles, inset 2 px, in the colour each key is drawn.
function inks() {
  const colours = {};
  for (const command of frame()) {
    for (const [key, [x, y, w, h]] of Object.entries(RECTS)) {
      if (command.text === undefined && Math.abs(command.a - (x + 2)) < 0.01 && Math.abs(command.b - (y + 2)) < 0.01 &&
        Math.abs(command.c - (w - 4)) < 0.01) colours[key] = command.color;
    }
  }
  return colours;
}

try {
  handle = api.nw_api_v1_create(id, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n);
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 3n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "By Ear"));
  const note = new TextDecoder().decode(view(api.nw_by_ear_options_note(pointer, capacity, 13n)));
  assert.equal(note, "Rung 13: 7 notes.  Play it from the lit key.  Some notes come in pairs.");
  assert.ok(api.nw_by_ear_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(api.nw_by_ear_options_apply(handle, 1n, 1n, 0n), 1n);

  // Keys do nothing before the run starts, nor does Enter; Space starts it,
  // and does nothing more. The keys do nothing while the tune plays.
  assert.equal(press(7), 2n);
  assert.equal(dispatch(EVENT.keyDown, KEY.enter), 2n);
  assert.equal(info(0), 0);
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  assert.equal(info(0), 1);
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 2n);
  assert.deepEqual([info(11), info(13), info(14), info(16), info(17)], [2, -1, 1, 2900, 12900]);
  let shown = texts();
  assert.ok(shown.includes("Listen...") && shown.includes("rung 1  1/1   2 notes"), shown.join(" | "));
  until(1000);
  assert.equal(press(7), 2n, "listening");
  assert.equal(clickKey(7), 2n, "listening");
  assert.equal(info(15), 0);
  // The autopilot's keys: G at 3.25 s and E at 3.3 s.
  until(3250);
  assert.equal(info(14), 0);
  assert.ok(texts().includes("Play it back: 0 of 2"));
  assert.equal(press(7), 1n);
  assert.deepEqual([info(10), info(15)], [1, 1]);
  assert.equal(inks()[7], 0x82c8faff, "a key just pressed is blue");
  tick();
  assert.equal(press(4), 1n);
  assert.equal(press(4), 2n, "the try is over");
  tick();
  assert.equal(info(0), 2);
  assert.deepEqual([info(8), info(9), info(10)], [1, 3300, 2]);
  assert.ok(texts().includes("All 2 played back"));
  assert.ok(silent(0, 0.79), "nothing before the tune");
  assert.ok(!silent(0.8, 1.0) && !silent(1.7, 1.9), "the tune's two notes");
  assert.ok(silent(2.9, 3.24), "nothing after the tune until the first key");
  assert.ok(!silent(3.25, 3.3), "the first key");
  assert.ok(!silent(3.6, 3.8), "the bell of a tune played back");
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
  assert.ok(texts().some(text => text.startsWith("1 of 1 passed")));
  assert.equal(api.nw_api_v1_destroy(handle), 0n);

  // Rung 10, heard six keys higher and played back by clicks from the lit
  // key: G#, F, E, A, D#, E.
  handle = api.nw_api_v1_create(id, 1n, 10n, 1n, 0n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n, String(handle));
  now = 0n;
  assert.equal(click(456, 100), 1n, "a click starts the run");
  assert.deepEqual([info(11), info(13), info(16), info(17)], [6, 8, 4100, 26100]);
  assert.notEqual(inks()[8], 0xfad25aff, "the lit key is not lit while the tune plays");
  until(4200);
  assert.equal(inks()[8], 0xfad25aff, "the lit key is gold once the tune has played");
  assert.equal(click(40, 300), 2n, "outside the keys");
  assert.equal(click(456 + 48, 600), 2n, "above the keys");
  for (const [n, key] of [8, 5, 4, 9, 3, 4].entries()) {
    assert.equal(clickKey(key), 1n, String(key));
    assert.equal(info(10), n + 1);
    tick();
  }
  assert.equal(info(0), 2);
  assert.equal(info(8), 1);
  assert.ok(texts().includes("All 6 played back"));
  assert.equal(api.nw_api_v1_destroy(handle), 0n);

  // Rung 13: G#, F, then the pair A and E with only A pressed. The pair
  // falls apart 0.45 s after its first key.
  handle = api.nw_api_v1_create(id, 1n, 13n, 1n, 0n, 0n, 0n, 0n, 17n);
  now = 0n;
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  until(4500);
  for (const key of [8, 5, 9]) {
    assert.equal(press(key), 1n, String(key));
    tick();
  }
  assert.deepEqual([info(10), info(12)], [2, 512]);
  until(4950);
  assert.equal(info(0), 1);
  until(5100);
  assert.equal(info(0), 2);
  assert.equal(info(8), 3);
  assert.ok(texts().includes("Both notes of a pair, together"));
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
const environment = createByEarEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 13);
  assert.ok(environment.act(7).ok, "a key port");
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("By Ear WASM menu, options note, Space start, keys ignored while the tune plays, a tune played back by "
  + "the autopilot's keys with its notes and bell, a shifted tune clicked back from the gold key, a pair let fall "
  + "apart, and hold");
