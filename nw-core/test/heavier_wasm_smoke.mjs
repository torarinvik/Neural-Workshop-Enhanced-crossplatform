import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createHeavierEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_heavier();
assert.equal(task, 3748814279n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => api.nw_api_v1_heavier_info(handle, BigInt(field));
let sequence = 0n;
let now = 0n;
function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function commands() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)));
}
function dispatch(kind, code, x = 0, y = 0, value = 0, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), BigInt(value),
    0n, BigInt(flags), BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
}
function tick(dt) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}

try {
  assert.equal(TASK_IDS_BY_CATEGORY[4][21], "heavier");
  assert.ok(decode(view(api.nw_taskhub_write(pointer, capacity, 4n, 21n, 0n, 912n, 684n)))
    .some(command => command.text === "Heavier"));
  assert.equal(new TextDecoder().decode(view(api.nw_heavier_options_note(pointer, capacity, 4n))),
    "Rung 4: 3 crates, 5 boards.  Each floor grips differently.");
  assert.ok(commands().some(command => command.text === "Press Space or click to start"));
  assert.equal(dispatch(5, 0, 456, 342), 1n);
  assert.ok(commands().some(command => command.text === "Board 1 of 5: which crate is heaviest?"));
  assert.equal(dispatch(5, 0, 160, 460), 1n);
  assert.equal(info(13), 0n);
  assert.equal(tick(100), 1n);
  assert.ok(info(14) > 0n);
  assert.equal(dispatch(4, 0, 160, 340, 1), 1n);
  assert.equal(info(13), 1n);
  assert.equal(dispatch(2, 12), 1n);
  assert.equal(info(13), 0n); // A held number takes priority over a mouse push.
  assert.equal(dispatch(3, 12), 1n);
  assert.equal(info(13), 1n);
  assert.equal(dispatch(6, 0, 160, 340), 1n);
  assert.equal(info(13), -1n);
  assert.equal(dispatch(2, 13), 1n);
  assert.equal(dispatch(9, 0), 1n);
  assert.equal(info(13), -1n);
  assert.equal(dispatch(2, 85, 0, 0, 0, 1), 2n); // Repeated C never re-answers.
  assert.equal(info(10), 0n);
  assert.equal(dispatch(5, 0, 820, 490), 1n);
  const seconds = Number(info(9)) / 1000;
  assert.ok(view(api.nw_heavier_audio_window(handle, seconds, seconds + 0.1, pointer, capacity))
    .some(byte => byte !== 0));
  assert.equal(tick(25), 1n);
  if (info(0) === 1n) {
    assert.equal(dispatch(2, 85), 1n); // C is also an answer during play.
    assert.equal(tick(25), 1n);
  }
  assert.equal(info(0), 2n);
  assert.ok(commands().some(command => command.text.includes("was the heaviest")));
  assert.equal(tick(2499), 2n);
  assert.equal(tick(1), 1n);
  assert.equal(info(0), 3n);
  assert.equal(api.nw_heavier_options_apply(handle, 13n, 3n, 0n), 1n);
  assert.equal(dispatch(2, 1), 1n);
  assert.equal(info(1), 13n);
  assert.equal(info(3), 3n);
  assert.equal(info(12), 4n);
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  api.nw_frame_free(pointer);
}

const canvas = { width: 228, height: 171 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, moveTo() {}, lineTo() {}, closePath() {},
  clearRect() {}, fillRect() {}, fillText() {},
  getImageData: () => ({ data: pixels }),
};
const env = createHeavierEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(env.n_actions, 8);
  assert.ok(env.act(2).ok);
  assert.equal(env.advance().done, false);
} finally {
  env.close();
}
console.log("PASS: Heavier WASM menu, mouse drag and answers, keyboard, audio, settings, and agent");
