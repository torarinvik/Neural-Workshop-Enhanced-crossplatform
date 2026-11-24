import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createPotterEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_potters_wheel();
assert.equal(id, 4292812816n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[2].indexOf("potters_wheel");
assert.equal(position, 25);

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
function info(field) {
  return Number(api.nw_api_v1_potters_wheel_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, x = 0, y = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, 0n,
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
}
function tick(dt) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 2n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Potter's Wheel"));
  const note = new TextDecoder().decode(view(api.nw_potters_wheel_options_note(pointer, capacity, 13n)));
  assert.equal(note, "Rung 13: 10 bands.  The clay dries.  The pot wanted is not drawn over the clay.");
  assert.ok(frame().some(command => command.text === "Press Space or click to start"));
  assert.equal(api.nw_potters_wheel_options_apply(handle, 4n, 1n, 1n), 1n);
  assert.equal(dispatch(2, 2), 1n);
  assert.equal(info(0), 1);
  assert.equal(info(11), 6);
  assert.ok(frame().some(command => command.text === "wet"));
  assert.equal(dispatch(2, 4), 1n);
  assert.equal(info(10), 2);
  assert.equal(dispatch(2, 6), 1n);
  assert.equal(info(10), 1);
  assert.equal(dispatch(2, 4), 1n);
  const clayY = 179 + (110 + 330 / 12) * 389 / 640;
  assert.equal(dispatch(5, 0, 456, clayY), 1n);
  assert.equal(info(14), 1);
  assert.equal(tick(100), 1n);
  assert.equal(info(13), 0);
  assert.ok(info(12) < 1000);
  assert.ok(frame().some(command => command.color === 0xecc8aae6));
  assert.equal(dispatch(11), 1n);
  assert.equal(info(14), 0);
  assert.equal(dispatch(2, 1), 1n);
  assert.equal(info(12), 1000);
  assert.ok(view(api.nw_potters_wheel_audio_window(handle, 0, 0.1, pointer, capacity)).some(byte => byte));
  assert.equal(dispatch(5, 0, 456, clayY), 1n);
  for (let i = 0; i < 20 && info(0) === 1; i++) tick(100);
  assert.equal(info(0), 2);
  assert.equal(info(8), 2);
  assert.equal(info(1), 3);
  assert.ok(frame().some(command => command.text === "The pot collapsed" && command.color === 0xff4040ff));
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
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
const environment = createPotterEnvironment(context, { seed: 17, rung: 4, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 17);
  assert.ok(environment.act(14).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Potter's Wheel WASM menu, options, keyboard, pointer, PCM, feedback, and stepped environment passed");
