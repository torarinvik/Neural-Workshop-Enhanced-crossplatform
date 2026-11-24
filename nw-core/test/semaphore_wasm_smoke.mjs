import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

// Semaphore through the browser ABI: the hub card, the options note (the
// reference's taskoptions.semaphore_note text, including the CPython '%.1f'
// rounding of 4.65 at rung 25), Space/Enter starting the run, letters arriving
// as text events in either case, non-letters refused, a letter typed while the
// flags are at rest struck as a mismatch, a signal struck once only, a whole
// message to its verdict, the verdict painted the way the info fields say,
// PCM, and the judged hold.

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createSemaphoreEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_semaphore();
assert.equal(id, 64710845n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[2].indexOf("semaphore");
assert.equal(position, TASK_IDS_BY_CATEGORY[2].indexOf("air_hockey") + 1);

const KEY = { space: 1, enter: 2 };
const handle = api.nw_api_v1_create(id, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
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
  return Number(api.nw_api_v1_semaphore_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, BigInt(flags), 0n, 0n, 0n);
}
function type(character) {
  return api.nw_api_v1_dispatch(handle, 8n, now, sequence++, 0n, BigInt(character.codePointAt(0)), 0n, 0n, 0n, 0n, 0n);
}
function tick(dt) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 2n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Semaphore"));
  const note = new TextDecoder().decode(view(api.nw_semaphore_options_note(pointer, capacity, 25n)));
  assert.equal(note, "Rung 25: 8 letters, 4.7 seconds each.  The signaller sometimes turns their back.  No chart.");
  assert.ok(api.nw_semaphore_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(api.nw_semaphore_options_apply(handle, 1n, 1n, 1n), 1n);

  // Letters do nothing before the run starts; Enter starts it.
  assert.equal(type("q"), 2n);
  assert.equal(dispatch(2, KEY.enter), 1n);
  assert.equal(info(0), 1);
  assert.ok(texts().includes("Copy each signal with your flags and type its letter"));
  assert.equal(info(11), 4);
  const allowed = info(13);
  assert.ok(allowed >= 1, String(allowed));

  // Wait for the first signal; a letter now, with the flags at rest, is a mismatch.
  for (let i = 0; i < 400 && info(15) < 0; i++) tick(16);
  const first = info(15);
  assert.ok(first >= 0, "no signal came up");
  assert.equal(type("7"), 2n, "a digit is not a letter");
  assert.equal(type(" "), 2n, "a space is not a letter");
  assert.equal(info(12), 0);
  assert.equal(type("Q"), 1n);
  assert.equal(info(12), 1, "a letter typed with the flags at rest is struck");
  // The reason is the verdict's: mid-run a strike is only a red disc.
  assert.ok(!texts().includes("Your flags do not match"), texts().join(" | "));
  type("q");
  assert.equal(info(12), 1, "a struck signal is not struck again");
  // Space during play is neither a letter nor a restart.
  assert.equal(dispatch(2, KEY.space), 2n);
  assert.equal(info(0), 1);

  // Strike every signal that comes up the same way: the run fails on the
  // strike that uses up the allowance, with that mismatch as its reason.
  for (let i = 0; i < 20000 && info(0) === 1; i++) {
    if (info(15) >= 0) type("q");
    tick(16);
  }
  assert.equal(info(0), 2);
  assert.equal(info(8), 2, "failed");
  assert.equal(info(12), allowed);
  const painted = texts();
  assert.ok(painted.includes("Your flags do not match"), painted.join(" | "));
  let sound = false;
  for (let begin = 0; begin + 1 <= info(9) / 1000 && !sound; begin += 1) {
    const length = api.nw_semaphore_audio_window(handle, begin, begin + 1, pointer, capacity);
    assert.ok(length >= 0n, String(length));
    if (length > 0n) sound = view(length).some(byte => byte);
  }
  assert.ok(sound, "a whole message made no sound");
  assert.equal(type("q"), 2n, "letters are refused once the run is judged");
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
  assert.ok(texts().some(text => text.startsWith("0 of 1 passed")), texts().join(" | "));
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
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
const environment = createSemaphoreEnvironment(context, { seed: 17, rung: 4, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 40);
  assert.ok(environment.act(39).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Semaphore WASM menu, options note, Space/Enter start, text-event letters, mismatch strikes, verdict, PCM, and hold");
