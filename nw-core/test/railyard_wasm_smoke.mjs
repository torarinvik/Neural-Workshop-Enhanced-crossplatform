import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createRailYardEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_railyard();
assert.equal(task, 3428277734n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 2n, 1n, 0n, 0n, 0n, 0n, 17n), -3n);
const handle = api.nw_api_v1_create(task, 1n, 16n, 1n, 0n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let sequence = 0n;
const info = field => api.nw_api_v1_railyard_info(handle, BigInt(field));
function view(length) {
  assert.ok(length > 0n && length <= capacity);
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function labels(dark = 0n) {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, dark, 912n, 684n)))
    .map(command => command.text).filter(text => text !== undefined);
}
function dispatch(kind, code, time, mods = 0n, x = 0, y = 0) {
  return api.nw_api_v1_dispatch(handle, kind, BigInt(time), sequence++, code, 0n, mods, 0n,
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
}
const advance = (time, dt) => api.nw_api_v1_advance(handle, BigInt(time), BigInt(dt), sequence++);

try {
  assert.equal(TASK_IDS_BY_CATEGORY[5][8], "rail_yard");
  const hub = decode(view(api.nw_taskhub_write(pointer, capacity, 5n, 8n, 0n, 912n, 684n)));
  assert.ok(hub.some(command => command.text === "Rail Yard"));
  const note = new TextDecoder().decode(view(api.nw_railyard_options_note(pointer, capacity, 16n)));
  assert.match(note, /8 stations, 10 trains, two tunnels.*Express trains catch up/);
  assert.ok(labels().includes("Press Space or click to start"));
  assert.equal(dispatch(5n, 2n, 0), 2n);
  assert.equal(dispatch(2n, 1n, 0), 1n);
  assert.equal(dispatch(2n, 12n, 0), 1n);
  assert.equal(advance(100, 100), 1n);
  assert.equal(dispatch(2n, 64n, 100), 1n);
  for (let now = 200; now <= 600; now += 100) assert.equal(advance(now, 100), 1n);
  assert.equal(dispatch(5n, 2n, 600, 0n, 195.0, 438.5), 1n);
  assert.equal(advance(700, 100), 1n);
  assert.equal(dispatch(2n, 65n, 700), 1n);
  let now = 700;
  while (info(0) === 1n && now < 100000) {
    now += 100;
    assert.equal(advance(now, 100), 1n);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(7), 3n);
  assert.equal(info(6), 0n);
  assert.equal(now, 77700);
  assert.ok(labels(1n).includes("Time: 0 of 10 trains home"));
  assert.equal(advance(now + 2999, 2999), 2n);
  assert.equal(advance(now + 3000, 1), 1n);
  assert.ok(labels().includes("0 of 1 passed   highest rung passed 0"));
  assert.equal(api.nw_railyard_options_apply(handle, 4n, 1n, 0n), 1n);
  assert.equal(dispatch(5n, 0n, now + 3001, 0n, 456, 342), 1n);
  assert.equal(info(0), 1n);
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  assert.equal(info(0), -1n);
  api.nw_frame_free(pointer);
}
console.log("Rail Yard WASM: hub, lights, keyboard, pointer, clock, Python timeout verdict, and restart pass");

const canvas = { width: 228, height: 171 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const context = {
  canvas, labels: [],
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, moveTo() {}, lineTo() {}, closePath() {},
  clearRect() { pixels.fill(0); this.labels.length = 0; },
  fillRect() {},
  fillText(text) {
    this.labels.push(text);
    const rgba = this.fillStyle === "rgba(64,255,64,1.000)" ? [64, 255, 64, 255]
      : this.fillStyle === "rgba(255,64,64,1.000)" ? [255, 64, 64, 255] : null;
    if (rgba) {
      pixels.set(rgba, pixels.length - 4);
      pixels.set(rgba, pixels.length - 4 - canvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};

assert.throws(() => createRailYardEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
const run = createRailYardEnvironment(context, { seed: 17, rung: 16, trials: 1, frameHz: 20 });
try {
  assert.equal(run.n_actions, 17);
  assert.ok(context.labels.includes("Every train to the station of its colour"));
  // Python at 20 Hz with repeated requests to throw the first set of points.
  for (let tick = 0; tick < 94; tick++) {
    assert.equal(run.step(0)[0].outcome, undefined);
  }
  const receipt = run.act(0);
  assert.ok(receipt.ok);
  assert.equal(run.act(0).ok, false);
  const verdict = run.advance();
  assert.equal(verdict.outcome.receipt_id, receipt.receipt_id);
  assert.equal(verdict.outcome.scalar, -1);
  assert.ok(run.verify(verdict.outcome, verdict));
  assert.ok(context.labels.includes("Train 1 derailed on points that were still moving"));
  assert.ok(context.labels.some(label => label.includes("home 0 of 10")));
  assert.ok(run.advance().done);
  assert.equal(run.reset(17).done, false);
} finally {
  run.close();
}
console.log("Rail Yard stepped WASM: 17 ports, 95 clocked ticks, verified verdict, completion, and reset pass");
