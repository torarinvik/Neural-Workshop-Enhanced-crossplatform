import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createDockingEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_docking();
assert.equal(task, 935767654n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let sequence = 0n;
const info = field => api.nw_api_v1_docking_info(handle, BigInt(field));
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
  assert.equal(TASK_IDS_BY_CATEGORY[5][15], "docking");
  assert.ok(decode(view(api.nw_taskhub_write(pointer, capacity, 5n, 15n, 0n, 912n, 684n)))
    .some(command => command.text === "Docking"));
  assert.match(new TextDecoder().decode(view(api.nw_docking_options_note(pointer, capacity, 20n))),
    /within 0\.14 m, under 0\.21 m\/s.*No readouts/);
  assert.ok(labels().includes("Press Space or click to start"));
  assert.equal(dispatch(5, 2, 0), 2n);
  assert.equal(dispatch(5, 0, 0), 1n);
  const fuel = info(11);
  const x = info(12);
  assert.equal(dispatch(2, 81, 0), 1n); // R requests forward thrust.
  assert.equal(dispatch(2, 77, 0), 1n); // A takes precedence.
  assert.equal(advance(100, 100), 1n);
  assert.equal(info(11), fuel - 100n);
  assert.equal(dispatch(3, 77, 100), 1n);
  assert.equal(advance(200, 100), 1n);
  assert.equal(info(11), fuel - 200n);
  assert.ok(info(12) < x);
  assert.equal(dispatch(2, 84, 200), 1n);
  assert.equal(dispatch(9, 0, 200), 1n);
  assert.equal(advance(300, 100), 1n);
  assert.equal(info(11), fuel - 200n);
  assert.equal(dispatch(2, 1, 300), 2n);
  let now = 300;
  while (info(0) === 1n && now < 49000) {
    now += 100;
    assert.equal(advance(now, 100), 1n);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(8), 2n);
  assert.equal(info(9), 1n);
  assert.ok(labels(1n).some(label => label.startsWith("Hit the port: ")));
  const pcmLength = api.nw_docking_contact_audio(handle, pointer, capacity);
  assert.equal(pcmLength, 70560n);
  assert.ok(view(pcmLength).some(byte => byte !== 0));
  assert.equal(advance(now + 2499, 2499), 2n);
  assert.equal(advance(now + 2500, 1), 1n);
  assert.ok(labels().includes("0 of 1 passed   highest rung passed 0"));
  assert.equal(api.nw_docking_contact_audio(handle, pointer, capacity), 0n);
  assert.equal(api.nw_docking_options_apply(handle, 20n, 1n, 0n), 1n);
  assert.equal(dispatch(2, 1, now + 2501), 1n);
  assert.equal(info(6), 20n);
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  api.nw_frame_free(pointer);
}

const agent = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 1n, 0n, 0n, 17n);
try {
  assert.ok(agent > 0n);
  assert.equal(api.nw_docking_agent_event(agent, 0, 12n), 1n);
  assert.equal(api.nw_docking_agent_event(agent, 0, 11n), 1n);
  assert.equal(api.nw_docking_agent_event(agent, 0.1, -1n), 1n);
  assert.equal(api.nw_api_v1_docking_info(agent, 17n), -1n);
  assert.equal(api.nw_docking_agent_event(agent, 0.2, -1n), 1n);
  assert.equal(api.nw_api_v1_docking_info(agent, 17n), -2n);
  let tick = 2;
  while (api.nw_api_v1_docking_info(agent, 0n) === 1n && tick < 485) {
    tick++;
    assert.equal(api.nw_docking_agent_event(agent, tick / 10, -1n), 1n);
  }
  assert.equal(api.nw_api_v1_docking_info(agent, 8n), 2n);
  assert.equal(api.nw_docking_agent_event(agent, (tick + 1) / 10, -1n), 1n);
  assert.equal(api.nw_api_v1_docking_info(agent, 0n), 3n);
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
const env = createDockingEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(env.n_actions, 12);
  assert.ok(env.act(4).ok);
  assert.equal(env.advance().done, false);
} finally {
  env.close();
}
console.log("Docking WASM: Planning hub, held-key priority, blur, timed feedback, and stepped agent pass");
