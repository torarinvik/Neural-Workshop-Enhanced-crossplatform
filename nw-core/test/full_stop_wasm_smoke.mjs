import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createFullStopEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_full_stop();
assert.equal(task, 3891758761n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => api.nw_api_v1_full_stop_info(handle, BigInt(field));
let sequence = 0n;
let now = 0n;
function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function commands() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)));
}
function dispatch(kind, code, x = 0, y = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, 0n,
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
}
function tick(dt) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}

try {
  assert.equal(TASK_IDS_BY_CATEGORY[4][22], "full_stop");
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 4n, 22n, 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Full Stop"));
  assert.equal(new TextDecoder().decode(view(api.nw_full_stop_options_note(pointer, capacity, 4n))),
    "Rung 4: 3 sentences run together.");
  assert.ok(commands().some(command => command.text === "Press Space or click to start"));
  assert.equal(dispatch(5, 0, 456, 342), 1n);
  const words = commands().filter(command => command.text && command.color === 0x282430ff);
  assert.ok(words.length >= 2);
  assert.equal(dispatch(5, 0, words[0].a, words[0].b), 1n);
  assert.equal(info(10), 1n);
  assert.equal(dispatch(6, 0, words[0].a, words[0].b), 1n);
  assert.ok(view(api.nw_full_stop_audio_window(handle, 0, 0.1, pointer, capacity)).some(byte => byte !== 0));
  assert.equal(dispatch(2, 9), 1n);
  assert.equal(info(10), 0n);
  assert.equal(dispatch(2, 2), 1n);
  assert.equal(tick(25), 1n);
  assert.equal(info(0), 2n);
  assert.ok(view(api.nw_full_stop_audio_window(handle, 0.2, 0.3, pointer, capacity)).some(byte => byte !== 0));
  assert.equal(tick(3999), 2n);
  assert.equal(tick(1), 1n);
  assert.equal(info(0), 3n);
  assert.equal(api.nw_full_stop_options_apply(handle, 13n, 3n, 0n), 1n);
  assert.equal(dispatch(2, 1), 1n);
  assert.equal(info(1), 13n);
  assert.equal(info(3), 3n);
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  api.nw_frame_free(pointer);
}

const cached = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 17n);
assert.ok(cached > 0n);
const passage = new TextEncoder().encode("Ada built a wooden boat. Clara painted it bright red.\n".repeat(100));
const source = api.nw_frame_alloc(BigInt(passage.length));
assert.ok(source > 0n);
try {
  new Uint8Array(api.memory.buffer, Number(source), passage.length).set(passage);
  assert.equal(api.nw_full_stop_load(cached, source, BigInt(passage.length), 0n, 0n, 0n, 0n), 1n);
  assert.equal(api.nw_full_stop_load(cached, source, BigInt(passage.length), 0n, 0n, 0n, 0n), 2n);
} finally {
  api.nw_frame_free(source);
}
assert.equal(api.nw_api_v1_dispatch(cached, 2n, 0n, 0n, 1n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
const frame = api.nw_frame_alloc(capacity);
try {
  const length = api.nw_api_v1_render(cached, frame, capacity, 1n, 912n, 684n);
  const commands = decode(new Uint8Array(api.memory.buffer, Number(frame), Number(length)));
  assert.ok(commands.some(command => command.text === "Ada"));
} finally {
  api.nw_frame_free(frame);
  assert.equal(api.nw_api_v1_destroy(cached), 0n);
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
const env = createFullStopEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(env.n_actions, 16);
  assert.ok(env.act(2).ok);
  assert.equal(env.advance().done, false);
} finally {
  env.close();
}
console.log("PASS: Full Stop WASM menu, cache import, pointer, keyboard, audio, settings, and agent");
