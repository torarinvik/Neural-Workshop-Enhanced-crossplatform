import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

// Claw Machine through the browser ABI: the hub card, the options notes
// (the reference's taskoptions.clawmachine_note), Space starting and Left
// not; then a rung-1 trolley moved left by a held Left for a second and out
// by a held Down for half of one, dropped with Enter and judged a miss to
// the right; the side view; the knock of the drop; a rung-1 try won by the
// reference autopilot's ports; and the agent's five ports. Every number
// below is the reference's (clawmachine.py driven tick for tick, 50 ms
// sub-stepped at 1/120 s).

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createClawMachineEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_claw_machine();
assert.equal(id, 2783635748n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[3].indexOf("claw_machine");
assert.equal(position, TASK_IDS_BY_CATEGORY[3].indexOf("cricket_hunt") + 1);

const KEY = { space: 1, enter: 2, left: 3, down: 6 };
const EVENT = { keyDown: 2, keyUp: 3, pointerMove: 4, pointerDown: 5 };
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
  return Number(api.nw_api_v1_claw_machine_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, BigInt(flags), 0n, 0n, 0n);
}
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
function note(rung) {
  return new TextDecoder().decode(view(api.nw_claw_machine_options_note(pointer, capacity, BigInt(rung))));
}
function silent(begin, end) {
  const length = api.nw_claw_machine_audio_window(handle, begin, end, pointer, capacity);
  assert.ok(length > 0n, String(length));
  return view(length).every(byte => byte === 0);
}

try {
  handle = api.nw_api_v1_create(id, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n);
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 3n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Claw Machine"));
  assert.equal(note(1), "Rung 1: 5 prizes.  A side view.");
  assert.equal(note(7), "Rung 7: 7 prizes.  The claw swings.");
  assert.ok(api.nw_claw_machine_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));

  // Left and Enter do nothing before the run starts; Space starts it.
  assert.equal(dispatch(EVENT.keyDown, KEY.left), 2n);
  assert.equal(dispatch(EVENT.keyDown, KEY.enter), 2n);
  assert.equal(info(0), 0);
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  assert.deepEqual([info(0), info(10), info(12), info(13), info(16)], [1, 0, 900, 1500, 5]);
  const shown = texts();
  assert.ok(shown.includes("Drop the claw over the gold prize") && shown.includes("rung 1  1/1   40 s") &&
    shown.includes("side view"), shown.join(" | "));
  // Left for a second, Down (out) for half of one.
  hold(KEY.left, 20);
  assert.deepEqual([info(12), info(13)], [350, 1500]);
  hold(KEY.down, 10);
  assert.deepEqual([info(12), info(13)], [350, 1225]);
  // A pointer move does nothing; Enter drops; the claw comes down and
  // closes 27 ticks later, to the right of the gold prize.
  assert.equal(pointerAt(EVENT.pointerMove, 500, 300, 1), 2n);
  assert.equal(dispatch(EVENT.keyDown, KEY.enter), 1n);
  assert.equal(info(10), 1);
  assert.equal(dispatch(EVENT.keyDown, KEY.enter), 2n, "one drop a try");
  for (let i = 0; i < 26; i++) tick();
  assert.equal(info(0), 1);
  tick();
  assert.deepEqual([info(0), info(8), info(11)], [2, 5, 1454]);
  assert.ok(texts().includes("Missed: to the right"));
  assert.ok(!silent(1.5, 1.7), "the knock of the drop");
  assert.ok(!silent(2.85, 3.05), "the growl of a miss");
  assert.equal(api.nw_api_v1_destroy(handle), 0n);

  // Rung 1 by the autopilot's ports: left, then out and left in turn
  // until over the gold prize, dropped, and got.
  handle = api.nw_api_v1_create(id, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 17n);
  now = 0n;
  assert.equal(pointerAt(EVENT.pointerDown, 456, 100, 1), 1n, "a click starts the run");
  const ports = [...Array(19).fill(0)];
  for (let i = 0; i < 11; i++) ports.push(3, 0);
  ports.push(3, 4, ...Array(26).fill(-1));
  for (const port of ports) {
    if (port >= 0) assert.equal(api.nw_claw_machine_agent_event(handle, Number(now) / 1000, BigInt(port)), 1n, String(port));
    tick();
  }
  assert.equal(now, 3450n);
  assert.deepEqual([info(0), info(8)], [2, 1]);
  assert.ok(texts().includes("Got it"));
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
const environment = createClawMachineEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 5);
  assert.ok(environment.act(0).ok, "the left port");
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Claw Machine WASM menu, options notes, Space start, the trolley moved by held keys, Enter's drop missed "
  + "to the right, the side view, the knock and the growl, a rung-1 try got by the autopilot's ports, and hold");
