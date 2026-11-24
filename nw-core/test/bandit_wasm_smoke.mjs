import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createExploreOrExploitEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_explore_exploit();
assert.equal(task, 3798735432n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 2n, 1n, 0n, 0n, 0n, 0n, 17n), -3n);
const handle = api.nw_api_v1_create(task, 1n, 16n, 1n, 0n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let sequence = 0n;
const info = field => api.nw_api_v1_explore_exploit_info(handle, BigInt(field));
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
const advance = time => api.nw_api_v1_advance(handle, BigInt(time), 0n, sequence++);

try {
  assert.equal(TASK_IDS_BY_CATEGORY[7][4], "explore_exploit");
  const hub = decode(view(api.nw_taskhub_write(pointer, capacity, 7n, 4n, 0n, 912n, 684n)));
  assert.ok(hub.some(command => command.text === "Explore or Exploit"));
  const note = new TextDecoder().decode(view(api.nw_explore_exploit_options_note(pointer, capacity, 16n)));
  assert.equal(note, "Rung 16: 6 machines, 60 pulls.  Means drift.  Dealt afresh every 18 pulls.  Payouts shown in fives.");
  assert.ok(labels().includes("Press Space or click to start"));
  assert.equal(dispatch(5n, 2n, 0, 92, 334), 2n);
  assert.equal(dispatch(2n, 1n, 0), 1n);
  assert.equal(api.nw_explore_exploit_options_apply(handle, 4n, 1n, 0n), 2n);
  assert.equal(dispatch(2n, 19n, 0), 2n);
  for (let pull = 1; pull <= 60; pull++) {
    const accepted = pull === 2 ? dispatch(5n, 0n, pull, 92, 334) : dispatch(2n, 12n, pull);
    assert.equal(accepted, 1n, `pull ${pull}`);
    if (pull === 2) {
      assert.ok(labels().includes("?"));
      assert.ok(labels().includes("0 coins     58 pulls left"));
    }
    if (pull === 5) {
      assert.ok(labels().includes("17 coins     55 pulls left"));
      assert.ok(!labels().includes("?"));
    }
  }
  assert.equal(info(0), 2n);
  assert.equal(info(4), 60n);
  assert.equal(info(5), 204n);
  const state = view(api.nw_api_v1_read_state(handle, pointer, capacity));
  const packet = new DataView(state.buffer, state.byteOffset, state.byteLength);
  assert.deepEqual(Array.from({ length: 10 }, (_, field) => packet.getBigInt64(16 + field * 8, true)),
    Array.from({ length: 10 }, (_, field) => info(field)));
  assert.ok(labels(1n).includes("204 coins (par 311)"));
  assert.equal(advance(3059), 2n);
  assert.equal(advance(3060), 1n);
  assert.equal(info(0), 3n);
  assert.ok(labels().includes("0 of 1 passed   highest rung passed 0"));
  assert.equal(api.nw_explore_exploit_options_apply(handle, 2n, 1n, 0n), -3n);
  assert.equal(api.nw_explore_exploit_options_apply(handle, 4n, 1n, 0n), 1n);
  assert.equal(dispatch(5n, 0n, 3061, 456, 342), 1n);
  assert.equal(info(0), 1n);
  assert.ok(labels().includes("40 pulls: collect as many coins as you can"));
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  assert.equal(info(0), -1n);
  api.nw_frame_free(pointer);
}
console.log("Explore or Exploit WASM: hub, original input, seeded batch, verdict, feedback deadline, and restart pass");

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

const run = createExploreOrExploitEnvironment(context, { seed: 17, rung: 16, trials: 1, adaptive: false });
try {
  assert.equal(run.n_actions, 8);
  assert.equal(run.step(7)[0].outcome, undefined);
  assert.ok(context.labels.includes("0 coins     60 pulls left"));
  for (let pull = 1; pull < 60; pull++) {
    assert.equal(run.step(0)[0].outcome, undefined);
    if (pull === 4) assert.ok(context.labels.includes("0 coins     56 pulls left"));
    if (pull === 5) assert.ok(context.labels.includes("17 coins     55 pulls left"));
  }
  const receipt = run.act(0);
  assert.ok(receipt.ok);
  assert.equal(run.act(0).ok, false);
  const verdict = run.advance();
  assert.equal(verdict.outcome.receipt_id, receipt.receipt_id);
  assert.equal(verdict.outcome.scalar, -1);
  assert.ok(run.verify(verdict.outcome, verdict));
  assert.ok(context.labels.includes("204 coins (par 311)"));
  assert.ok(run.advance().done);
  assert.equal(run.reset(17).done, false);
} finally {
  run.close();
}

const timed = createExploreOrExploitEnvironment(context, {
  rung: 16, seed: 17, trials: 2, frameHz: 20, thinkSeconds: 0.1, refillSeconds: 0.05,
});
try {
  assert.equal(timed.advance().outcome, undefined);
  const first = timed.advance();
  assert.equal(first.outcome.scalar, -1);
  assert.ok(timed.verify(first.outcome, first));
  assert.ok(context.labels.includes("Out of time"));
  assert.equal(timed.forfeits, 1);
  assert.equal(timed.advance().done, false);
  assert.equal(timed.think_left, 0.05);
  assert.ok(context.labels.some(label => label.startsWith("rung 16  run 2/2")));
  const second = timed.advance();
  assert.equal(second.outcome.scalar, -1);
  assert.ok(timed.verify(second.outcome, second));
  assert.equal(timed.forfeits, 2);
  assert.ok(timed.advance().done);
  assert.ok(context.labels.includes("0 of 0 passed   highest rung passed 0"));
  assert.ok(!context.labels.includes("Out of time"));
} finally {
  timed.close();
}
console.log("Explore or Exploit stepped WASM: eight ports, batch updates, receipts, think clock, refill, and reset pass");
