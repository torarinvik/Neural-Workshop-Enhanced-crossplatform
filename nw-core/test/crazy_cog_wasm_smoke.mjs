import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createCrazyCogEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_crazy_cog();
assert.equal(task, 205861782n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[4].indexOf("crazy_cog");
assert.equal(position, 26);

const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => Number(api.nw_api_v1_crazy_cog_info(handle, BigInt(field)));
let sequence = 0n;
let now = 0n;
function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function frame() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)));
}
function dispatch(kind, code = 0, x = 0, y = 0, modifiers = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, BigInt(modifiers), 0n,
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
}
function tick(dt) {
  now += BigInt(dt);
  assert.ok(api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++) > 0n);
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 4n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Crazy Cog"));
  const note = new TextDecoder().decode(view(api.nw_crazy_cog_options_note(pointer, capacity, 20n)));
  assert.equal(note, "Rung 20: a load of 3.1.  Chains.  2 walls.  A back layer and shared axles.  A fan to turn.");
  assert.ok(frame().some(command => command.text === "Press Space or click to start"));
  assert.equal(api.nw_crazy_cog_options_apply(handle, 20n, 1n, 1n), 1n);
  assert.equal(dispatch(2, 1), 1n);
  assert.equal(info(0), 1);
  assert.equal(info(11), 3);
  const state = view(api.nw_api_v1_read_state(handle, pointer, capacity));
  const fields = new DataView(state.buffer, state.byteOffset, state.byteLength);
  assert.equal(fields.getUint32(0, true), 0x3152574e);
  assert.equal(fields.getBigInt64(16 + 11 * 8, true), 3n);
  assert.equal(dispatch(2, 23), 1n);
  assert.equal(info(10), 1);
  assert.equal(dispatch(2, 23, 0, 0, 1), 1n);
  assert.equal(info(10), 0);
  assert.equal(dispatch(2, 14), 1n);
  assert.equal(info(10), 2);
  assert.equal(dispatch(2, 87), 1n);
  assert.equal(info(10), 0);
  assert.equal(dispatch(2, 88), 1n);
  assert.equal(info(10), 2);
  assert.equal(dispatch(2, 12), 1n);
  const first = frame().find(command => command.text?.endsWith(" teeth"));
  assert.ok(first);
  const trayY = first.b - 40 * 389 / 640;
  assert.equal(dispatch(5, 0, first.a, trayY), 1n);
  assert.ok(info(12) > 0);
  assert.equal(dispatch(4, 0, 456, 300), 1n);
  assert.equal(dispatch(6, 0, first.a, trayY), 1n);
  assert.equal(info(12), 0);
  assert.equal(dispatch(5, 0, first.a, trayY), 1n);
  assert.equal(dispatch(11), 1n);
  assert.equal(info(12), 0);
  assert.equal(dispatch(2, 9), 1n);
  assert.ok(view(api.nw_crazy_cog_audio_window(handle, 0, 0.1, pointer, capacity)).some(byte => byte !== 0));
  for (let step = 0; step < 5000 && info(0) === 1; step++) tick(100);
  assert.equal(info(0), 2, `simulation time ${info(9)} ms`);
  assert.equal(info(8), 3);
  assert.equal(info(1), 19);
  assert.ok(frame().some(command => command.text === "Out of time"));
  tick(2500);
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
const environment = createCrazyCogEnvironment(context, { seed: 17, rung: 20, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 17);
  assert.ok(environment.act(15).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Crazy Cog WASM menu, settings, keyboard, drag, PCM, timeout, and stepped environment passed");
