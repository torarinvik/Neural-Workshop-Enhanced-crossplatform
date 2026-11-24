import assert from "node:assert/strict";
import fs from "node:fs";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createSonarEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_sonar();
assert.equal(task, 3424761748n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 7n, 1n, 1n, 0n, 0n, 0n, 17n), -3n);

const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
function view(length) {
  assert.ok(length > 0n && length <= capacity, `invalid frame length ${length}`);
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function session(rung) {
  const run = api.nw_api_v1_create(task, 1n, BigInt(rung), 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(run > 0n);
  let sequence = 0n;
  return {
    close() { assert.equal(api.nw_api_v1_destroy(run), 0n); },
    info(field) { return api.nw_api_v1_sonar_info(run, BigInt(field)); },
    frame() { return decode(view(api.nw_api_v1_render(run, pointer, capacity, 0n, 912n, 684n))); },
    dispatch(kind, code, time, x = 0, y = 0, modifiers = 0n) {
      return api.nw_api_v1_dispatch(run, kind, time, sequence++, code, 0n, modifiers, 0n,
        BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
    },
    advance(time) { return api.nw_api_v1_advance(run, time, 0n, sequence++); },
  };
}

try {
  const category = TASK_IDS_BY_CATEGORY.findIndex(ids => ids.includes("sonar"));
  assert.deepEqual(TASK_IDS_BY_CATEGORY[category], ["sonar", "dispatch", "gamble", "bluff", "explore_exploit", "firebreak", "crossroads", "triage", "dam_keeper"]);
  const hub = decode(view(api.nw_taskhub_write(pointer, capacity, BigInt(category), 0n, 0n, 912n, 684n)));
  assert.ok(hub.some(command => command.text === "Sonar"));
  assert.equal(new TextDecoder().decode(view(api.nw_sonar_options_note(pointer, capacity, 25n))),
    "Rung 25: a 24x24 grid, a wrong dig costs 24 pings.  30% of readings are off by one band.  The target drifts.  You must beat the reference player.");

  const run = session(1);
  try {
    assert.ok(run.frame().some(command => command.text === "Press Space to start"));
    assert.equal(run.dispatch(5n, 0n, 0n, 456, 370), 2n);
    assert.equal(run.dispatch(2n, 1n, 1n), 1n);
    assert.equal(run.info(5), 12n);
    assert.equal(run.info(8), 12n); // Python par is 6.
    assert.equal(run.dispatch(2n, 4n, 2n), 1n);
    assert.equal(run.info(5), 7n);
    assert.equal(run.dispatch(2n, 32n, 3n), 1n);
    assert.equal(run.info(7), 1n);
    assert.equal(run.dispatch(5n, 2n, 4n, 456, 370), 1n);
    assert.equal(run.info(7), 4n);
    assert.equal(run.dispatch(5n, 0n, 5n, 598.8, 302.1, 1n), 1n);
    assert.equal(run.info(0), 2n);
    assert.equal(run.info(11), 1n);
    const frame = run.frame();
    assert.ok(frame.some(command => command.text === "Found for 4; par was 6" && command.color === 0x40ff40ff));
    assert.ok(frame.some(command => command.text === "★"));
    assert.equal(run.advance(1804n), 2n);
    assert.equal(run.advance(1805n), 1n);
    assert.ok(run.frame().some(command => command.text === "1 of 1 under par   highest rung passed 1"));
    assert.equal(run.dispatch(2n, 1n, 1806n), 1n);
    assert.equal(run.info(0), 1n);
    assert.equal(run.info(7), 0n);
  } finally {
    run.close();
  }

  const large = session(25);
  try {
    assert.equal(large.dispatch(2n, 1n, 0n), 1n);
    assert.equal(large.info(4), 24n);
    assert.equal(large.info(8), 259n); // Python par is 129.5.
    assert.ok(large.frame().filter(command => command.kind === Kind.POLYGON).length >= 24 * 24);
  } finally {
    large.close();
  }
} finally {
  api.nw_frame_free(pointer);
}

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

const env = createSonarEnvironment(context, { seed: 17, trials: 1 });
try {
  assert.equal(env.n_actions, 6);
  // The Python board starts at (2, 2) and the seeded target is (4, 3).
  for (const port of [4, 3, 3, 1]) assert.equal(env.step(port)[0].outcome, undefined);
  const receipt = env.act(5);
  assert.ok(receipt.ok);
  assert.equal(env.act(4).ok, false);
  const verdict = env.advance();
  assert.equal(verdict.outcome.scalar, 1);
  assert.equal(verdict.outcome.receipt_id, receipt.receipt_id);
  assert.ok(env.verify(verdict.outcome, verdict));
  assert.ok(context.labels.includes("Found for 1; par was 6"));
  const done = env.advance();
  assert.equal(done.done, true);
  assert.equal(done.outcome, undefined);
  assert.equal(env.reset(17).done, false);
} finally {
  env.close();
}

const timed = createSonarEnvironment(context, {
  rung: 25, seed: 17, trials: 2, frameHz: 20, thinkSeconds: 0.1, refillSeconds: 0.05,
});
try {
  assert.ok(context.labels.includes("Find it for 129.5 or less"));
  assert.equal(timed.step()[0].outcome, undefined);
  const timeout = timed.step()[0];
  assert.equal(timeout.outcome.scalar, -1);
  assert.ok(timed.verify(timeout.outcome, timeout));
  assert.equal(timed.forfeits, 1);
  assert.equal(timed.advance().done, false);
  assert.equal(timed.think_left, 0.05);
  assert.ok(context.labels.some(label => label.startsWith("rung 25  2/2")));
  const second = timed.step()[0];
  assert.equal(second.outcome.scalar, -1);
  assert.ok(timed.verify(second.outcome, second));
  const done = timed.advance();
  assert.equal(done.done, true);
  assert.equal(done.outcome, undefined);
  assert.ok(context.labels.includes("0 of 0 under par   highest rung passed 0"));
  assert.ok(!context.labels.includes("Out of time"));
} finally {
  timed.close();
}

console.log("sonar_wasm_smoke: PASS (interactive controls, largest board, stepped receipts, clock, forfeits, and restart)");
