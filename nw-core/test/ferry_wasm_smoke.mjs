import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createFerryEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_ferry();
assert.equal(task, 709946811n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let sequence = 0n;
const info = field => api.nw_api_v1_ferry_info(handle, BigInt(field));
function view(length) {
  assert.ok(length > 0n && length <= capacity);
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function labels(dark = 0n) {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, dark, 912n, 684n)))
    .map(command => command.text).filter(text => text !== undefined);
}
function dispatch(kind, code, time) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), BigInt(time), sequence++, BigInt(code), 0n,
    0n, 0n, 500000n, 500000n, 0n);
}
const advance = (time, dt) => api.nw_api_v1_advance(handle, BigInt(time), BigInt(dt), sequence++);

try {
  assert.equal(TASK_IDS_BY_CATEGORY[5][14], "ferry");
  assert.ok(decode(view(api.nw_taskhub_write(pointer, capacity, 5n, 13n, 0n, 912n, 684n)))
    .some(command => command.text === "Ferry"));
  assert.match(new TextDecoder().decode(view(api.nw_ferry_options_note(pointer, capacity, 20n))),
    /3 crossings, a 2\.2 m\/s river, 3 lane.*Gusts.*Fog hides the barges/);
  assert.ok(labels().includes("Press Space or click to start"));
  assert.equal(dispatch(5, 2, 0), 2n);
  assert.equal(dispatch(5, 0, 0), 1n);
  assert.equal(dispatch(2, 3, 0), 1n); // Left arrow.
  assert.equal(dispatch(2, 77, 0), 1n); // A also holds left.
  assert.equal(dispatch(2, 79, 0), 1n); // W combines ahead and left.
  assert.equal(dispatch(3, 3, 0), 1n);
  assert.equal(advance(100, 100), 1n);
  assert.equal(info(14), 95500n);
  assert.equal(dispatch(3, 77, 100), 1n);
  assert.equal(advance(200, 100), 1n);
  assert.equal(info(14), 95500n);
  assert.equal(dispatch(2, 78, 200), 1n);
  assert.equal(dispatch(9, 0, 200), 1n); // Blur clears throttle and turn.
  assert.equal(advance(300, 100), 1n);
  assert.equal(info(14), 95500n);
  assert.equal(dispatch(2, 1, 300), 2n); // Space only starts a run.
  let now = 300;
  while (info(0) === 1n && now < 131000) {
    now += 100;
    assert.equal(advance(now, 100), 1n);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(7), 3n);
  assert.ok(labels(1n).includes("Swept out of the harbour"));
  assert.equal(advance(now + 2999, 2999), 2n);
  assert.equal(advance(now + 3000, 1), 1n);
  assert.ok(labels().includes("0 of 1 passed   highest rung passed 0"));
  assert.equal(api.nw_ferry_options_apply(handle, 20n, 1n, 0n), 1n);
  assert.equal(dispatch(2, 1, now + 3001), 1n);
  assert.equal(info(5), 3n);
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  api.nw_frame_free(pointer);
}

const agent = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 1n, 0n, 0n, 17n);
try {
  assert.ok(agent > 0n);
  assert.equal(api.nw_ferry_agent_event(agent, 0, 6n), 1n);
  assert.equal(api.nw_ferry_agent_event(agent, 0, 5n), 1n);
  assert.equal(api.nw_ferry_agent_event(agent, 0.05, -1n), 1n);
  assert.equal(api.nw_api_v1_ferry_info(agent, 14n), 87250n);
  assert.equal(api.nw_ferry_agent_event(agent, 0.1, -1n), 1n);
  assert.equal(api.nw_api_v1_ferry_info(agent, 14n), 87250n);
  let tick = 2;
  while (api.nw_api_v1_ferry_info(agent, 0n) === 1n && tick < 2640) {
    tick++;
    assert.equal(api.nw_ferry_agent_event(agent, tick / 20, -1n), 1n);
  }
  assert.equal(api.nw_api_v1_ferry_info(agent, 7n), 3n);
  assert.equal(api.nw_ferry_agent_event(agent, (tick + 1) / 20, -1n), 1n);
  assert.equal(api.nw_api_v1_ferry_info(agent, 0n), 3n);
} finally {
  assert.equal(api.nw_api_v1_destroy(agent), 0n);
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
const env = createFerryEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(env.n_actions, 6);
  assert.ok(env.act(4).ok);
  assert.equal(env.advance().done, false);
} finally {
  env.close();
}
console.log("Ferry WASM: Planning hub, combined controls, blur, timed feedback, and stepped agent pass");
