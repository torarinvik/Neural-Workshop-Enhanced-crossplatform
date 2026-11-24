import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createKitchenEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_kitchen();
assert.equal(task, 870733615n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 1n, 2n, 0n, 0n, 0n, 0n, 17n), -3n);
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let sequence = 0n;
const info = field => api.nw_api_v1_kitchen_info(handle, BigInt(field));
function view(length) {
  assert.ok(length > 0n && length <= capacity);
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function labels(dark = 0n) {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, dark, 912n, 684n)))
    .map(command => command.text).filter(text => text !== undefined);
}
function dispatch(kind, code, time, x = 0, y = 0) {
  return api.nw_api_v1_dispatch(handle, kind, BigInt(time), sequence++, code, 0n, 0n, 0n,
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
}
const advance = (time, dt) => api.nw_api_v1_advance(handle, BigInt(time), BigInt(dt), sequence++);

try {
  assert.equal(TASK_IDS_BY_CATEGORY[5][12], "kitchen");
  const hub = decode(view(api.nw_taskhub_write(pointer, capacity, 5n, 12n, 0n, 912n, 684n)));
  assert.ok(hub.some(command => command.text === "Kitchen"));
  assert.match(new TextDecoder().decode(view(api.nw_kitchen_options_note(pointer, capacity, 25n))),
    /7 tickets.*3 stove.*burns after 2.5 s/);
  assert.ok(labels().includes("Press Space or click to start"));
  assert.equal(dispatch(5n, 2n, 0, 456, 342), 2n);
  assert.equal(dispatch(5n, 0n, 0, 456, 342), 1n);
  assert.equal(dispatch(2n, 14n, 0), 2n); // Crate 3 is absent at rung 1.
  // The reference cook's orders for seed 17 at 100 ms per tick.
  const orders = new Map([
    [21, 1], [30, 4], [51, 4], [52, 6], [104, 6], [105, 9], [109, 9], [110, 11],
    [223, 1], [242, 4], [263, 4], [264, 6], [316, 6], [317, 9], [321, 9], [322, 11],
    [443, 0], [463, 4], [483, 4], [484, 6], [536, 6], [537, 9], [541, 9], [542, 11],
  ]);
  let now = 0;
  for (let tick = 0; tick < 549; tick++) {
    const port = orders.get(tick);
    if (tick === 30) {
      assert.equal(dispatch(5n, 2n, now, 314, 457), 1n); // The active board accepts right clicks.
    } else if (port !== undefined) {
      assert.equal(dispatch(2n, BigInt(port < 4 ? 12 + port : 68 + port - 4), now), 1n);
    }
    now += 100;
    assert.equal(advance(now, 100), 1n);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(4), 3n);
  assert.equal(info(5), 0n);
  assert.equal(info(7), 1n);
  assert.ok(labels(1n).includes("Shift done: 3 of 3 served"));
  assert.equal(advance(now + 2999, 2999), 2n);
  assert.equal(advance(now + 3000, 1), 1n);
  assert.ok(labels().includes("1 of 1 passed   highest rung passed 1"));
  assert.equal(api.nw_kitchen_options_apply(handle, 30n, 1n, 0n), 1n);
  assert.equal(dispatch(2n, 1n, now + 3001), 1n);
  assert.equal(info(6), 8n);
  assert.ok(labels().includes("T"));
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  assert.equal(info(0), -1n);
  api.nw_frame_free(pointer);
}

const agent = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 1n, 0n, 0n, 17n);
assert.ok(agent > 0n);
const agentInfo = field => api.nw_api_v1_kitchen_info(agent, BigInt(field));
try {
  assert.equal(api.nw_kitchen_agent_event(agent, 0, 13n), 1n);
  assert.equal(api.nw_kitchen_agent_event(agent, 0, 12n), 1n);
  assert.equal(api.nw_kitchen_agent_event(agent, 0, 10n), 2n);
  for (let tick = 1; tick <= 1566; tick++) {
    assert.equal(api.nw_kitchen_agent_event(agent, tick / 20, -1n), 1n);
    assert.equal(agentInfo(7), tick < 1566 ? 0n : 2n);
  }
  assert.equal(api.nw_kitchen_agent_event(agent, 1567 / 20, -1n), 1n);
  assert.equal(agentInfo(0), 3n);
} finally {
  assert.equal(api.nw_api_v1_destroy(agent), 0n);
}

// Exercise the session arena with repeated create, deal, and destroy calls.
function dealAndClose() {
  const run = api.nw_api_v1_create(task, 1n, 30n, 1n, 0n, 1n, 0n, 0n, 17n);
  assert.ok(run > 0n);
  assert.equal(api.nw_kitchen_agent_event(run, 0, 13n), 1n);
  assert.equal(api.nw_api_v1_kitchen_info(run, 6n), 8n);
  assert.equal(api.nw_api_v1_destroy(run), 0n);
}
dealAndClose();
const warmBytes = api.memory.buffer.byteLength;
for (let trial = 0; trial < 24; trial++) dealAndClose();
assert.equal(api.memory.buffer.byteLength, warmBytes);

const canvas = { width: 228, height: 171 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, moveTo() {}, lineTo() {}, closePath() {},
  clearRect() {}, fillRect() {}, fillText() {},
  getImageData() { return { data: pixels }; },
};
const environment = createKitchenEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 13);
  assert.ok(environment.act(12).ok);
  assert.equal(environment.advance().done, false);
  assert.equal(environment.reset(17).done, false);
} finally {
  environment.close();
}
console.log("Kitchen WASM: Planning hub, controls, options, clocked feedback, restart, and stepped agent pass");
