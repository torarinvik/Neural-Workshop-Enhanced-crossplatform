import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createUnicycleEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_unicycle();
assert.equal(task, 2516562765n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let sequence = 0n;
const info = field => api.nw_api_v1_unicycle_info(handle, BigInt(field));
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
  assert.equal(TASK_IDS_BY_CATEGORY[5][17], "unicycle");
  assert.ok(decode(view(api.nw_taskhub_write(pointer, capacity, 5n, 17n, 0n, 912n, 684n)))
    .some(command => command.text === "Unicycle"));
  assert.match(new TextDecoder().decode(view(api.nw_unicycle_options_note(pointer, capacity, 20n))),
    /Ledges\./);
  assert.ok(labels().includes("Press Space or click to start"));
  assert.equal(dispatch(5, 2, 0), 2n);
  assert.equal(dispatch(5, 0, 0), 1n);
  assert.equal(dispatch(2, 4, 0), 1n);   // Up.
  assert.equal(dispatch(2, 77, 0), 1n);  // W also holds pedal.
  assert.equal(dispatch(2, 3, 0), 1n);   // Left.
  assert.equal(dispatch(3, 4, 0), 1n);
  assert.equal(advance(25, 25), 1n);
  assert.equal(info(9), 4n);             // Pedal and lean back.
  assert.equal(dispatch(2, 5, 25), 1n);  // Right cancels left.
  assert.equal(advance(50, 25), 1n);
  assert.equal(info(9), 0n);
  assert.equal(dispatch(9, 0, 50), 1n);
  assert.equal(advance(75, 25), 1n);
  assert.equal(info(9), -1n);
  let now = 75;
  while (info(0) === 1n && now < 2000) {
    now += 25;
    assert.equal(advance(now, 25), 1n);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(8), 2n);
  assert.ok(labels(1n).includes("Head over heels"));
  const pcmLength = api.nw_unicycle_contact_audio(handle, pointer, capacity);
  assert.equal(pcmLength, 70560n);
  assert.ok(view(pcmLength).some(byte => byte !== 0));
  assert.equal(advance(now + 2499, 2499), 2n);
  assert.equal(advance(now + 2500, 1), 1n);
  assert.ok(labels().includes("0 of 1 passed   highest rung passed 0"));
  assert.equal(api.nw_unicycle_contact_audio(handle, pointer, capacity), 0n);
  assert.equal(api.nw_unicycle_options_apply(handle, 20n, 1n, 0n), 1n);
  assert.equal(dispatch(2, 1, now + 2501), 1n);
  assert.equal(info(6), 20n);
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  api.nw_frame_free(pointer);
}

const agent = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 1n, 0n, 0n, 17n);
try {
  assert.ok(agent > 0n);
  assert.equal(api.nw_unicycle_agent_event(agent, 0, 8n), 1n);
  for (let tick = 0; tick < 3; tick++) {
    assert.equal(api.nw_unicycle_agent_event(agent, tick / 10, 7n), 1n);
    assert.equal(api.nw_unicycle_agent_event(agent, (tick + 1) / 10, -1n), 1n);
  }
  assert.equal(api.nw_api_v1_unicycle_info(agent, 0n), 2n);
  assert.equal(api.nw_api_v1_unicycle_info(agent, 8n), 2n);
  assert.equal(api.nw_api_v1_unicycle_info(agent, 10n), 292n);
  assert.equal(api.nw_unicycle_agent_event(agent, 0.4, -1n), 1n);
  assert.equal(api.nw_api_v1_unicycle_info(agent, 0n), 3n);
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
const env = createUnicycleEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(env.n_actions, 8);
  assert.ok(env.act(4).ok);
  assert.equal(env.advance().done, false);
} finally {
  env.close();
}
console.log("Unicycle WASM: Planning hub, combined controls, blur, timed feedback, and stepped agent pass");
