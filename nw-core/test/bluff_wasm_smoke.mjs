import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createBluffEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_bluff();
assert.equal(task, 3952940662n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 2n, 1n, 0n, 0n, 0n, 0n, 17n), -3n);
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let sequence = 0n;
const info = field => api.nw_api_v1_bluff_info(handle, BigInt(field));
function view(length) {
  assert.ok(length > 0n && length <= capacity);
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function labels(dark = 0n) {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, dark, 912n, 684n)))
    .filter(command => command.text !== undefined).map(command => command.text);
}
function dispatch(kind, code, time, x = 0, y = 0) {
  return api.nw_api_v1_dispatch(handle, kind, BigInt(time), sequence++, code, 0n, 0n, 0n,
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
}
const advance = time => api.nw_api_v1_advance(handle, BigInt(time), 0n, sequence++);

try {
  const hub = decode(view(api.nw_taskhub_write(pointer, capacity, 7n, 3n, 0n, 912n, 684n)));
  assert.deepEqual(hub.map(command => command.text).filter(text =>
    ["Sonar", "Dispatch", "Gamble", "Bluff", "Explore or Exploit", "Firebreak", "Crossroads", "Triage", "Dam Keeper"].includes(text)),
  ["Sonar", "Dispatch", "Gamble", "Bluff", "Explore or Exploit", "Firebreak", "Crossroads", "Triage", "Dam Keeper"]);
  assert.match(new TextDecoder().decode(view(api.nw_bluff_options_note(pointer, capacity, 3n))),
    /^Rung 3: 23 hands, cards 1 to 3\./);
  assert.ok(labels().includes("Press Space or click to start"));
  assert.equal(dispatch(5n, 2n, 0, 100, 342), 2n);
  assert.equal(dispatch(2n, 1n, 0), 1n);
  assert.equal(api.nw_bluff_options_apply(handle, 3n, 1n, 0n), 2n);
  for (let action = 1; action <= 22; action++) {
    const accepted = action === 2 ? dispatch(5n, 0n, action, 356, 208)
      : dispatch(2n, action % 2 ? 12n : 13n, action);
    assert.equal(accepted, 1n, `action ${action}`);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(4), 21n);
  assert.equal(info(5), 10n);
  const state = view(api.nw_api_v1_read_state(handle, pointer, capacity));
  const packet = new DataView(state.buffer, state.byteOffset, state.byteLength);
  assert.deepEqual(Array.from({ length: 10 }, (_, field) => packet.getBigInt64(16 + field * 8, true)),
    Array.from({ length: 10 }, (_, field) => info(field)));
  assert.ok(labels(1n).includes("Your play was worth 8 against a par of 15 (chips +10) -- they were: station"));
  assert.equal(advance(3021), 2n);
  assert.equal(advance(3022), 1n);
  assert.equal(info(0), 3n);
  assert.ok(labels().includes("0 of 1 at par or better   highest rung passed 0"));
  assert.equal(api.nw_bluff_options_apply(handle, 2n, 1n, 0n), -3n);
  assert.equal(api.nw_bluff_options_apply(handle, 3n, 1n, 0n), 1n);
  assert.equal(info(0), 0n);
  assert.equal(dispatch(5n, 0n, 3023, 456, 342), 1n);
  assert.equal(info(0), 1n);
  assert.equal(info(4), 0n);
  // Python's second deal uses the same RNG after the first rung-one round.
  assert.ok(labels().includes("Play 23 hands worth 2.4 or more"));
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  assert.equal(info(0), -1n);
  api.nw_frame_free(pointer);
}
console.log("Bluff WASM: hub, options, keyboard and mouse, seeded verdict, feedback deadline, restart, and cleanup pass");

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

const run = createBluffEnvironment(context, { seed: 17, trials: 1, adaptive: false });
try {
  assert.equal(run.n_actions, 2);
  for (let move = 1; move < 22; move++) {
    assert.equal(run.step((move + 1) % 2)[0].outcome, undefined);
  }
  const receipt = run.act(1);
  assert.ok(receipt.ok);
  assert.equal(run.act(1).ok, false);
  const verdict = run.advance();
  assert.equal(verdict.outcome.receipt_id, receipt.receipt_id);
  assert.equal(verdict.outcome.scalar, -1);
  assert.ok(run.verify(verdict.outcome, verdict));
  assert.ok(context.labels.includes("Your play was worth 8 against a par of 15 (chips +10) -- they were: station"));
  assert.ok(run.advance().done);
  assert.equal(run.reset(17).done, false);
} finally {
  run.close();
}

const timed = createBluffEnvironment(context, {
  rung: 3, seed: 17, trials: 2, frameHz: 20, thinkSeconds: 0.1, refillSeconds: 0.05,
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
  assert.ok(context.labels.some(label => label.startsWith("rung 3  2/2")));
  const second = timed.advance();
  assert.equal(second.outcome.scalar, -1);
  assert.ok(timed.verify(second.outcome, second));
  assert.equal(timed.forfeits, 2);
  assert.ok(timed.advance().done);
  assert.ok(context.labels.includes("0 of 0 at par or better   highest rung passed 0"));
  assert.ok(!context.labels.includes("Out of time"));
} finally {
  timed.close();
}
console.log("Bluff stepped WASM: two action ports, verified verdicts, think clock, refill, and reset pass");
