import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createRoverEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_rover();
assert.equal(task, 3976448863n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let sequence = 0n;
const info = field => api.nw_api_v1_rover_info(handle, BigInt(field));
function view(length) {
  assert.ok(length > 0n && length <= capacity);
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function labels() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 0n, 912n, 684n)))
    .map(command => command.text).filter(text => text !== undefined);
}
function dispatch(kind, code, time) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), BigInt(time), sequence++, BigInt(code), 0n,
    0n, 0n, 500000n, 500000n, 0n);
}
const advance = (time, dt) => api.nw_api_v1_advance(handle, BigInt(time), BigInt(dt), sequence++);

try {
  assert.equal(TASK_IDS_BY_CATEGORY[5][16], "rover");
  assert.ok(decode(view(api.nw_taskhub_write(pointer, capacity, 5n, 16n, 0n, 912n, 684n)))
    .some(command => command.text === "Rover"));
  assert.match(new TextDecoder().decode(view(api.nw_rover_options_note(pointer, capacity, 4n))),
    /Rung 4: 1\.0 s delay, 3 flag\(s\)\.  8 rocks\./);
  assert.ok(labels().includes("Press Space or click to start"));
  assert.equal(dispatch(5, 2, 0), 2n);
  assert.equal(dispatch(5, 0, 0), 1n);
  assert.equal(dispatch(2, 4, 0), 1n);   // Up.
  assert.equal(dispatch(2, 77, 0), 1n);  // W also holds drive.
  assert.equal(dispatch(2, 80, 0), 1n);  // D has lower priority.
  assert.equal(dispatch(3, 4, 0), 1n);
  assert.equal(advance(100, 100), 1n);
  assert.equal(info(15), 0n);
  assert.ok(info(11) > 0n);
  assert.equal(advance(200, 100), 1n);
  assert.ok(info(15) > 0n);
  assert.equal(info(17), 0n);
  assert.equal(info(18), 0n);
  assert.equal(dispatch(9, 0, 200), 1n);
  assert.equal(advance(300, 100), 1n);
  assert.equal(advance(400, 100), 1n);
  assert.equal(info(11), 0n);
  assert.ok(info(17) > 0n);
  assert.ok(labels().includes("delay 0.2 s"));
  let now = 400;
  while (info(0) === 1n && now < 61000) {
    now += 100;
    assert.equal(advance(now, 100), 1n);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(8), 4n);
  assert.ok(labels().includes("0 of 1 flags"));
  assert.equal(advance(now + 2499, 2499), 2n);
  assert.equal(advance(now + 2500, 1), 1n);
  assert.ok(labels().includes("0 of 1 passed   highest rung passed 0"));
  assert.equal(api.nw_rover_options_apply(handle, 4n, 1n, 0n), 1n);
  assert.equal(info(0), 0n);
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
}

const agent = api.nw_api_v1_create(task, 1n, 4n, 1n, 0n, 1n, 0n, 0n, 17n);
const agentInfo = field => api.nw_api_v1_rover_info(agent, BigInt(field));
try {
  assert.ok(agent > 0n);
  assert.equal(api.nw_rover_agent_event(agent, 0, 4n), 1n);
  let tick = 0;
  while (agentInfo(0) === 1n && tick < 30) {
    assert.equal(api.nw_rover_agent_event(agent, tick / 10, 0n), 1n);
    tick++;
    assert.equal(api.nw_rover_agent_event(agent, tick / 10, -1n), 1n);
  }
  assert.equal(tick, 25);
  assert.equal(agentInfo(8), 2n);
  assert.equal(agentInfo(12), 2458n);
  const pcmLength = api.nw_rover_audio_window(agent, 2.45, 2.99, pointer, capacity);
  assert.equal(pcmLength, 47628n);
  assert.ok(view(pcmLength).some(byte => byte !== 0));
  assert.equal(api.nw_rover_agent_event(agent, (tick + 1) / 10, -1n), 1n);
  assert.equal(agentInfo(0), 3n);
} finally {
  assert.equal(api.nw_api_v1_destroy(agent), 0n);
  api.nw_frame_free(pointer);
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
const env = createRoverEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(env.n_actions, 4);
  assert.ok(env.act(3).ok);
  assert.equal(env.advance().done, false);
} finally {
  env.close();
}
console.log("Rover WASM: Planning hub, delay, held aliases, focus cleanup, feedback, audio, and stepped agent pass");
