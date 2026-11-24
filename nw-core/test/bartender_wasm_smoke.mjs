import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createBartenderEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_bartender();
assert.equal(id, 760738060n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[2].indexOf("bartender");
assert.equal(position, 29);

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
  return Number(api.nw_api_v1_bartender_info(handle, BigInt(field)));
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
  assert.ok(menu.some(command => command.text === "Bartender"));
  const note = new TextDecoder().decode(view(api.nw_bartender_options_note(pointer, capacity, 16n)));
  assert.equal(note, "Rung 16: 5 customers, 4 bottles.  Pour by ear.  Remember the usual.");
  assert.ok(frame().some(command => command.text === "Press Space or click to start"));
  assert.equal(api.nw_bartender_options_apply(handle, 1n, 1n, 1n), 1n);
  assert.equal(dispatch(2, 2), 1n);
  assert.equal(info(0), 1);
  const route = (kind, [x, y]) => dispatch(kind, 0, 456 + (x - 500) * 389 / 640, 179 + y * 389 / 640);
  const bottle = [208.68494, 375.26633];
  const glass = [237.18821, 304.17217];
  const back = [185.61858, 302.46625];
  while (now < 1050n) assert.equal(tick(50), 1n);
  assert.ok(frame().some(command => command.text === "Seat 1: a green."));
  assert.equal(dispatch(2, 1), 1n);
  assert.equal(info(16), 1);
  assert.equal(dispatch(2, 1), 1n);
  assert.equal(info(16), 0);
  assert.ok(view(api.nw_bartender_audio_window(handle, 1.05, 1.15, pointer, capacity)).some(byte => byte));

  assert.equal(route(5, bottle), 1n);
  assert.equal(info(15), 1);
  assert.equal(route(4, glass), 1n);
  for (let i = 0; i < 25; i++) assert.equal(tick(50), 1n);
  assert.equal(info(13), 500);
  assert.equal(route(6, glass), 1n);

  assert.equal(route(5, glass), 1n);
  assert.equal(route(4, back), 1n);
  tick(20);
  assert.equal(route(4, glass), 1n);
  tick(20);
  assert.equal(dispatch(11), 1n);
  assert.equal(info(14), 0);
  assert.equal(info(18), 0);

  assert.equal(route(5, glass), 1n);
  assert.equal(info(15), 5);
  assert.equal(route(4, back), 1n);
  tick(20);
  assert.equal(route(4, glass), 1n);
  tick(20);
  assert.equal(route(6, glass), 1n);
  assert.equal(info(18), 1);
  while (info(0) === 1 && now < 4000n) tick(50);
  assert.equal(info(10), 1);
  assert.equal(info(0), 2);
  assert.equal(info(8), 1);
  assert.ok(frame().some(command => command.text === "Last orders: a good night" && command.color === 0x40ff40ff));
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
  assert.equal(api.nw_bartender_options_apply(handle, 30n, 1n, 0n), 1n);
  assert.equal(dispatch(2, 2), 1n);
  assert.equal(info(0), 1);
  assert.equal(info(11), 9);
  assert.equal(info(10), 0);
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
const environment = createBartenderEnvironment(context, { seed: 17, rung: 4, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 15);
  assert.ok(environment.act(14).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Bartender WASM menu, options, pouring, ice, sliding, PCM, feedback, and stepped environment passed");
