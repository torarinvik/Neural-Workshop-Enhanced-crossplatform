import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

// Cricket Hunt through the browser ABI: the hub card, the options note (the
// reference's taskoptions.crickethunt_note), Space starting and W not; then
// a rung-1 room walked into by a held W for a second, turned by A, looked
// up by Q, a drag that turns and tilts the head, and a grab at nothing; the
// chirps sounding; and a rung-1 try caught by the reference autopilot's
// ports; and the agent's seven ports. Every number below is the
// reference's (crickethunt.py driven tick for tick, 50 ms sub-stepped at
// 1/120 s).

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createCricketHuntEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_cricket_hunt();
assert.equal(id, 3655954588n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[3].indexOf("cricket_hunt");
assert.equal(position, TASK_IDS_BY_CATEGORY[3].indexOf("piano_tuner") + 1);

const KEY = { space: 1, w: 77, a: 99, q: 101 };
const EVENT = { keyDown: 2, keyUp: 3, pointerMove: 4, pointerDown: 5, pointerUp: 6 };
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
  const frame = decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)));
  return frame.filter(command => command.text !== undefined).map(command => command.text);
}
function info(field) {
  return Number(api.nw_api_v1_cricket_hunt_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, BigInt(flags), 0n, 0n, 0n);
}
// A pointer event at reference pixels (x, y) from the bottom left; buttons
// is the page's event.buttons.
function pointerAt(kind, x, y, buttons = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, 0n, BigInt(buttons), 0n, 0n,
    BigInt(Math.round(x * 1000000 / 912)), BigInt(Math.round(y * 1000000 / 684)), 0n);
}
function tick(dt = 50) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}
function hold(key, ticks) {
  assert.equal(dispatch(EVENT.keyDown, key), 1n);
  for (let i = 0; i < ticks; i++) tick();
  assert.equal(dispatch(EVENT.keyUp, key), 1n);
}
function silent(begin, end) {
  const length = api.nw_cricket_hunt_audio_window(handle, begin, end, pointer, capacity);
  assert.equal(length, BigInt(Math.round((end - begin) * 22050) * 4));
  return view(length).every(byte => byte === 0);
}

try {
  handle = api.nw_api_v1_create(id, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n);
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 3n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Cricket Hunt"));
  const note = new TextDecoder().decode(view(api.nw_cricket_hunt_options_note(pointer, capacity, 13n)));
  assert.equal(note, "Rung 13: 4 cricket(s).  They hop.");
  assert.ok(api.nw_cricket_hunt_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(api.nw_cricket_hunt_audio_window(handle, 0, 0.1, pointer, capacity), 0n, "no sound before the run");

  // W does nothing before the run starts; Space starts it.
  assert.equal(dispatch(EVENT.keyDown, KEY.w), 2n);
  assert.equal(info(0), 0);
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  assert.deepEqual([info(0), info(11), info(13), info(14), info(15), info(16)], [1, 1, 3000, 3000, 391, 0]);
  const shown = texts();
  assert.ok(shown.includes("Find the crickets by their chirping") &&
    shown.includes("rung 1  1/1   caught 0 of 1   grabs left 3"), shown.join(" | "));
  // W for a second, A for half of one, Q for half of one.
  hold(KEY.w, 20);
  assert.deepEqual([info(13), info(14)], [3495, 4202]);
  hold(KEY.a, 10);
  assert.equal(info(15), -395);
  hold(KEY.q, 10);
  assert.equal(info(16), 524);
  assert.ok(!silent(0, 1), "the cricket chirps");
  // A drag 57 px right and 171 px up turns the head right and tilts it up
  // to the stop; a move without the button ends the drag.
  assert.equal(pointerAt(EVENT.pointerDown, 456, 171, 1), 2n);
  assert.equal(pointerAt(EVENT.pointerMove, 513, 342, 1), 1n);
  assert.deepEqual([info(15), info(16)], [-53, 1350]);
  assert.equal(pointerAt(EVENT.pointerMove, 456, 513, 0), 2n);
  assert.equal(pointerAt(EVENT.pointerMove, 456, 171, 1), 2n);
  assert.deepEqual([info(15), info(16)], [-53, 1350]);
  // A grab at nothing.
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  assert.deepEqual([info(0), info(8), info(12)], [1, 0, 1]);
  assert.ok(texts().includes("rung 1  1/1   caught 0 of 1   grabs left 2"));
  assert.equal(api.nw_api_v1_destroy(handle), 0n);

  // Rung 1 by the autopilot's ports: turned right, walked up, looked down,
  // caught at 2.6 s.
  handle = api.nw_api_v1_create(id, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 17n);
  now = 0n;
  assert.equal(pointerAt(EVENT.pointerDown, 456, 100, 1), 1n, "a click starts the run");
  for (const [port, count] of [[3, 25], [0, 2], [3, 1], [0, 18], [5, 6]]) {
    for (let i = 0; i < count; i++) {
      assert.equal(api.nw_cricket_hunt_agent_event(handle, Number(now) / 1000, BigInt(port)), 1n, String(port));
      tick();
    }
  }
  assert.equal(api.nw_cricket_hunt_agent_event(handle, Number(now) / 1000, 6n), 1n);
  assert.equal(now, 2600n);
  tick();
  assert.deepEqual([info(0), info(8), info(10)], [2, 1, 1]);
  assert.ok(texts().includes("All 1 caught in 3 s"));
  assert.ok(!silent(2.55, 2.65), "the bell of the catch");
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
const environment = createCricketHuntEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 7);
  assert.ok(environment.act(0).ok, "the forward port");
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Cricket Hunt WASM menu, options note, Space start, walking, turning and looking by held keys and a drag, "
  + "a grab at nothing, the chirps, a rung-1 try caught by the autopilot's ports, and hold");
