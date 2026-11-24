import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createLockPickEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_lock_pick();
assert.equal(id, 3800709530n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[2].indexOf("lock_pick");
assert.equal(position, 30);

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
  return Number(api.nw_api_v1_lock_pick_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, x = 0, y = 0, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, BigInt(flags),
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
}

function tick(dt) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 2n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Lock Pick"));
  const note = new TextDecoder().decode(view(api.nw_lock_pick_options_note(pointer, capacity, 16n)));
  assert.equal(note, "Rung 16: 6 pins.  Some clicks are false.  The pins are not shown.");
  assert.ok(frame().some(command => command.text === "Press Space or click to start"));
  assert.equal(api.nw_lock_pick_options_apply(handle, 1n, 1n, 1n), 1n);
  assert.equal(dispatch(2, 2), 1n);
  assert.ok(frame().some(command => command.text === "0 of 3 set"));
  assert.equal(dispatch(2, 1), 1n);
  assert.equal(dispatch(2, 98), 1n);
  assert.equal(info(15), 3);
  assert.equal(dispatch(2, 1, 0, 0, 1), 2n);
  tick(100);
  assert.equal(info(12), 90);
  assert.equal(dispatch(3, 1), 1n);
  tick(100);
  assert.equal(info(12), 180);
  assert.equal(dispatch(3, 98), 1n);
  tick(100);
  assert.equal(info(12), 130);
  assert.equal(dispatch(2, 1), 1n);
  tick(100);
  assert.equal(dispatch(11), 1n);
  assert.equal(info(15), 0);
  tick(100);
  assert.equal(info(12), 170);
  const screenX = x => 456 + (x - 500) * 389 / 640;
  const screenY = y => 179 + y * 389 / 640;
  assert.equal(dispatch(5, 0, screenX(250), screenY(230)), 1n);
  assert.ok(view(api.nw_lock_pick_audio_window(handle, 0.5, 0.6, pointer, capacity)).some(byte => byte));
  assert.equal(dispatch(6, 0, screenX(250), screenY(230)), 1n);
  assert.equal(dispatch(2, 1), 1n);
  for (let i = 0; i < 100 && info(0) === 1; i++) tick(100);
  assert.equal(info(0), 2);
  assert.equal(info(13), 3);
  assert.equal(info(8), 2);
  assert.ok(frame().some(command => command.text === "The wrench slipped once too often" && command.color === 0xff4040ff));
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  api.nw_frame_free(pointer);
}

const winning = api.nw_api_v1_create(id, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(winning > 0n);
const winPointer = api.nw_frame_alloc(capacity);
let winTime = 0n;
let winSequence = 0n;
const winInfo = field => Number(api.nw_api_v1_lock_pick_info(winning, BigInt(field)));
const winEvent = (kind, code = 0, x = 0, y = 0) =>
  api.nw_api_v1_dispatch(winning, BigInt(kind), winTime, winSequence++, BigInt(code), 0n, 0n, 0n,
    BigInt(Math.round((456 + (x - 500) * 389 / 640) * 1e6 / 912)),
    BigInt(Math.round((179 + y * 389 / 640) * 1e6 / 684)), 0n);
function winTick() {
  if (winInfo(12) < 480 && winInfo(15) === 0) winEvent(2, 1);
  if (winInfo(12) > 600 && winInfo(15) !== 0) winEvent(3, 1);
  winTime += 20n;
  assert.equal(api.nw_api_v1_advance(winning, winTime, 20n, winSequence++), 1n);
}
try {
  assert.equal(winEvent(2, 2), 1n);
  while (winInfo(12) < 480) winTick();
  for (const [pin, height] of [0.79, 0.74, 0.47].entries()) {
    assert.equal(winEvent(5, 0, 250 + 70 * pin, 230 + 170 * height), 1n);
    for (let i = 0; i < 20 && winInfo(10) === pin; i++) winTick();
    assert.equal(winInfo(10), pin + 1);
    winEvent(6, 0, 250 + 70 * pin, 230 + 170 * height);
  }
  assert.equal(winInfo(8), 1);
  const length = api.nw_api_v1_render(winning, winPointer, capacity, 1n, 912n, 684n);
  const painted = decode(new Uint8Array(api.memory.buffer, Number(winPointer), Number(length)));
  assert.ok(painted.some(command => command.text === "The lock turned" && command.color === 0x40ff40ff));
} finally {
  api.nw_api_v1_destroy(winning);
  api.nw_frame_free(winPointer);
}

const canvas = { width: 228, height: 171 };
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, moveTo() {}, lineTo() {}, closePath() {},
  clearRect() {}, fillRect() {}, fillText() {},
  getImageData: () => ({ data: new Uint8ClampedArray(canvas.width * canvas.height * 4) }),
};
const environment = createLockPickEnvironment(context, { seed: 17, rung: 4, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 15);
  assert.ok(environment.act(14).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Lock Pick WASM menu, options, tension aliases, key-up, focus, PCM, and slip verdict");
