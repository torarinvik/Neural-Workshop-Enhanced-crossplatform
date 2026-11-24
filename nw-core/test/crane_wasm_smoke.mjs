import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createCraneEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_crane();
assert.equal(task, 462731910n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let sequence = 0n;
const info = field => api.nw_api_v1_crane_info(handle, BigInt(field));
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
  assert.equal(TASK_IDS_BY_CATEGORY[5][13], "crane");
  assert.ok(decode(view(api.nw_taskhub_write(pointer, capacity, 5n, 13n, 0n, 912n, 684n)))
    .some(command => command.text === "Crane"));
  assert.match(new TextDecoder().decode(view(api.nw_crane_options_note(pointer, capacity, 20n))),
    /4 containers.*A stack stands in the way.*Wind pushes the load.*The ship rolls/);
  assert.ok(labels().includes("Press Space or click to start"));
  assert.equal(dispatch(2, 2, 0), 2n); // Enter grabs during play.
  assert.equal(dispatch(5, 2, 0), 2n);
  assert.equal(dispatch(5, 0, 0), 1n);
  assert.equal(dispatch(2, 5, 0), 1n); // Right arrow.
  assert.equal(dispatch(2, 78, 0), 1n); // D also holds right.
  assert.equal(dispatch(3, 5, 0), 1n);
  assert.equal(advance(100, 100), 1n);
  assert.equal(info(12), 16016n);
  assert.equal(dispatch(2, 79, 100), 1n); // Horizontal movement wins over hoisting.
  assert.equal(advance(200, 100), 1n);
  assert.equal(info(13), 6000n);
  assert.equal(dispatch(3, 78, 200), 1n);
  assert.equal(advance(300, 100), 1n);
  assert.equal(info(13), 5600n);
  assert.equal(dispatch(9, 0, 300), 1n); // Blur stops the remaining W.
  assert.equal(advance(400, 100), 1n);
  assert.equal(info(13), 5600n);
  assert.equal(dispatch(2, 2, 400), 1n);
  assert.equal(info(14), -1n);
  let now = 400;
  while (info(0) === 1n && now < 121000) {
    now += 100;
    assert.equal(advance(now, 100), 1n);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(7), 6n);
  assert.ok(labels(1n).includes("Out of time"));
  assert.equal(advance(now + 2999, 2999), 2n);
  assert.equal(advance(now + 3000, 1), 1n);
  assert.ok(labels().includes("0 of 1 passed   highest rung passed 0"));
  assert.equal(api.nw_crane_options_apply(handle, 20n, 1n, 0n), 1n);
  assert.equal(dispatch(2, 1, now + 3001), 1n);
  assert.equal(info(5), 4n);
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  api.nw_frame_free(pointer);
}

const agent = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 1n, 0n, 0n, 17n);
try {
  assert.ok(agent > 0n);
  assert.equal(api.nw_crane_agent_event(agent, 0, 5n), 1n);
  assert.equal(api.nw_crane_agent_event(agent, 0, 3n), 1n);
  assert.equal(api.nw_crane_agent_event(agent, 0.05, -1n), 1n);
  assert.equal(api.nw_api_v1_crane_info(agent, 13n), 6200n);
  assert.equal(api.nw_crane_agent_event(agent, 0.1, -1n), 1n);
  assert.equal(api.nw_api_v1_crane_info(agent, 13n), 6200n);
  let tick = 2;
  while (api.nw_api_v1_crane_info(agent, 0n) === 1n && tick < 2440) {
    tick++;
    assert.equal(api.nw_crane_agent_event(agent, tick / 20, -1n), 1n);
  }
  assert.equal(api.nw_api_v1_crane_info(agent, 7n), 6n);
  assert.equal(api.nw_crane_agent_event(agent, (tick + 1) / 20, -1n), 1n);
  assert.equal(api.nw_api_v1_crane_info(agent, 0n), 3n);
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
const env = createCraneEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(env.n_actions, 5);
  assert.ok(env.act(4).ok);
  assert.equal(env.advance().done, false);
} finally {
  env.close();
}
console.log("Crane WASM: Planning hub, held aliases, blur, grab, timed feedback, and stepped agent pass");
