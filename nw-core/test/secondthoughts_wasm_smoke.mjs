import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createSecondThoughtsEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_second_thoughts();
assert.equal(task, 2360688716n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(TASK_IDS_BY_CATEGORY[11][1], "second_thoughts");
assert.equal(api.nw_second_thoughts_load, undefined, "Second Thoughts imports nothing");

const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => api.nw_api_v1_second_thoughts_info(handle, BigInt(field));
let sequence = 0n;
let now = 0n;
function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function frame() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)));
}
function texts() {
  return frame().map(command => command.text).filter(Boolean);
}
function dispatch(kind, code = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, 0n, 0n, 0n, 0n);
}
function tick(dt) {
  now += BigInt(dt);
  assert.ok(api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++) > 0n);
}
function note(rung) {
  return new TextDecoder().decode(view(api.nw_second_thoughts_options_note(pointer, capacity, BigInt(rung))));
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 11n, 0n, 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Second Thoughts"));
  assert.ok(menu.some(command => command.text === "Rationality"));
  assert.equal(note(1), "Rung 1: race, pond, coin, counts.");
  assert.equal(note(13), "Rung 13: race, pond, coin, counts, bakers, price, description, hospital, percent, two_tests.");
  assert.ok(api.nw_second_thoughts_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(dispatch(2, 1), 1n);
  assert.equal(info(0), 1n);
  assert.ok(texts().includes("The first answer that comes to mind is not always right"));
  // Pressing 1 to every question: the deal never gives a round one number
  // pressed throughout would pass, so this fails, and fails early.
  let first = true;
  for (let i = 0; i < 400 && info(0) === 1n; i++) {
    if (info(11) + info(12) === info(10) && dispatch(2, 12) === 1n && first) {
      const shown = texts();
      assert.ok(shown.some(text => text.startsWith("Right: ") || text.startsWith("No: ")), shown.join(" | "));
      assert.ok(view(api.nw_second_thoughts_audio_window(handle, 0, 0.1, pointer, capacity)).some(byte => byte !== 0));
      first = false;
    }
    tick(50);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(4), 0n);
  assert.ok(info(12) >= 4n, String(info(12)));
  tick(2500);
  assert.equal(info(0), 3n);
  assert.ok(texts().includes("0 of 1 passed   highest rung passed 0"));
  assert.equal(api.nw_second_thoughts_options_apply(handle, 4n, 3n, 0n), 1n);
  assert.equal(info(3), 3n);
  assert.equal(info(6), 4n);
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
const environment = createSecondThoughtsEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 8);
  assert.ok(environment.act(0).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("PASS: Second Thoughts WASM Rationality tab, options notes, keys, a fixed answer's failed round, audio, " +
  "options and agent controls");
