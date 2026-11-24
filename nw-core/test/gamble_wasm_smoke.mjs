import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createGambleEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_gamble();
assert.equal(task, 816838233n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 2n, 1n, 0n, 0n, 0n, 0n, 17n), -3n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const text = new TextDecoder();
function view(length) {
  assert.ok(length > 0n && length <= capacity, `invalid frame length ${length}`);
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}

function session(rung) {
  const handle = api.nw_api_v1_create(task, 1n, BigInt(rung), 1n, 0n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n);
  let sequence = 0n;
  return {
    close() {
      assert.equal(api.nw_api_v1_destroy(handle), 0n);
      assert.equal(api.nw_api_v1_destroy(handle), 0n);
      assert.equal(api.nw_api_v1_gamble_info(handle, 0n), -1n);
    },
    info(field) { return api.nw_api_v1_gamble_info(handle, BigInt(field)); },
    state() {
      const data = view(api.nw_api_v1_read_state(handle, pointer, capacity));
      const packet = new DataView(data.buffer, data.byteOffset, data.byteLength);
      assert.equal(data.byteLength, 112);
      assert.equal(packet.getUint32(12, true), 12);
      return Array.from({ length: 10 }, (_, field) => packet.getBigInt64(16 + field * 8, true));
    },
    labels(dark = 0n) {
      return decode(view(api.nw_api_v1_render(handle, pointer, capacity, dark, 912n, 684n)))
        .filter(command => command.text !== undefined);
    },
    dispatch(kind, code, time, x = 0, y = 0) {
      return api.nw_api_v1_dispatch(handle, kind, time, sequence++, code, 0n, 0n, 0n,
        BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
    },
    advance(time) { return api.nw_api_v1_advance(handle, time, 0n, sequence++); },
  };
}

try {
  const category = TASK_IDS_BY_CATEGORY.findIndex(ids => ids.includes("gamble"));
  assert.deepEqual(TASK_IDS_BY_CATEGORY[category], ["sonar", "dispatch", "gamble", "bluff", "explore_exploit", "firebreak", "crossroads", "triage", "dam_keeper"]);
  const hub = decode(view(api.nw_taskhub_write(pointer, capacity, BigInt(category), 1n, 0n, 912n, 684n)));
  assert.ok(hub.some(command => command.text === "Gamble"));
  assert.match(text.decode(view(api.nw_gamble_options_note(pointer, capacity, 18n))),
    /^Rung 18: 7 machines, 59 pulls.*bankroll and Stop/);

  const paid = session(18);
  try {
    assert.ok(paid.labels().some(command => command.text === "Press Space or click to start"));
    assert.equal(paid.dispatch(5n, 2n, 0n, 100, 342), 2n);
    assert.equal(paid.dispatch(5n, 0n, 1n, 100, 342), 1n);
    assert.ok(paid.labels(1n).some(command => command.text === "Stop (S)"));
    assert.equal(paid.dispatch(2n, 12n, 2n), 1n);
    assert.equal(paid.dispatch(5n, 0n, 3n, 100, 342), 1n);
    assert.deepEqual(paid.state(), Array.from({ length: 10 }, (_, field) => paid.info(field)));
    assert.equal(paid.info(4), 2n);
    assert.equal(paid.dispatch(2n, 34n, 4n), 1n);
    assert.equal(paid.info(0), 2n);
    assert.ok(paid.labels().some(command => command.text.startsWith("Your pulls were worth") &&
      command.color === 0xff4040ff));
    assert.equal(paid.advance(3003n), 2n);
    assert.equal(paid.advance(3004n), 1n);
    assert.ok(paid.labels().some(command => command.text === "0 of 1 at par or better   highest rung passed 0"));
    assert.equal(paid.dispatch(2n, 1n, 3005n), 1n);
    assert.equal(paid.info(4), 0n);
    assert.equal(paid.dispatch(5n, 0n, 3006n, 456, 196.5), 1n);
    assert.equal(paid.info(0), 2n);
  } finally {
    paid.close();
  }

  const free = session(1);
  try {
    assert.equal(free.dispatch(2n, 1n, 0n), 1n);
    assert.ok(free.labels().some(command => command.text === "Make your pulls worth 20.1 or more"));
    assert.equal(free.dispatch(2n, 34n, 1n), 2n);
    assert.equal(free.dispatch(2n, 19n, 2n), 2n);
    assert.equal(free.info(4), 0n);
  } finally {
    free.close();
  }
} finally {
  api.nw_frame_free(pointer);
}
console.log("Gamble WASM: hub, options, pulls, both Stop inputs, timed verdict, and restart pass");

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

const winning = createGambleEnvironment(context, { seed: 17, trials: 1 });
try {
  assert.equal(winning.n_actions, 9);
  // The source deal at rung 1 has 25 pulls, and its second arm beats par.
  assert.equal(winning.step(8)[0].outcome, undefined);
  assert.equal(winning.step(7)[0].outcome, undefined);
  for (let pull = 0; pull < 24; pull++) assert.equal(winning.step(1)[0].outcome, undefined);
  const receipt = winning.act(1);
  assert.ok(receipt.ok);
  assert.equal(winning.act(1).ok, false);
  const verdict = winning.advance();
  assert.equal(verdict.outcome.receipt_id, receipt.receipt_id);
  assert.equal(verdict.outcome.scalar, 1);
  assert.ok(winning.verify(verdict.outcome, verdict));
  assert.ok(context.labels.includes("Your pulls were worth 22 against a par of 20.1   (coins won 23)"));
  assert.ok(winning.advance().done);
  assert.equal(winning.reset(17).done, false);
} finally {
  winning.close();
}

const timed = createGambleEnvironment(context, {
  rung: 18, seed: 17, trials: 2, frameHz: 20, thinkSeconds: 0.1, refillSeconds: 0.05,
});
try {
  assert.equal(timed.step()[0].outcome, undefined);
  const flag = timed.step()[0];
  assert.equal(flag.outcome.scalar, -1);
  assert.ok(timed.verify(flag.outcome, flag));
  assert.ok(context.labels.includes("Out of time"));
  assert.equal(timed.forfeits, 1);
  assert.equal(timed.advance().done, false);
  assert.equal(timed.think_left, 0.05);
  assert.ok(context.labels.some(label => label.startsWith("rung 18  2/2")));
  const loss = timed.step(8)[0];
  assert.equal(loss.outcome.scalar, -1);
  assert.ok(timed.verify(loss.outcome, loss));
  assert.ok(context.labels.some(label => label.startsWith("Your pulls were worth")));
  assert.equal(timed.forfeits, 1);
  const done = timed.advance();
  assert.equal(done.done, true);
  assert.equal(done.outcome, undefined);
  assert.ok(context.labels.includes("0 of 1 at par or better   highest rung passed 0"));
} finally {
  timed.close();
}
const allForfeit = createGambleEnvironment(context, { rung: 25, trials: 1, frameHz: 20, thinkSeconds: 0.05 });
try {
  const flag = allForfeit.advance();
  assert.equal(flag.outcome.scalar, -1);
  assert.ok(allForfeit.verify(flag.outcome, flag));
  const done = allForfeit.advance();
  assert.ok(done.done);
  assert.equal(done.outcome, undefined);
  assert.ok(context.labels.includes("0 of 0 at par or better   highest rung passed 0"));
  assert.ok(!context.labels.includes("Out of time"));
} finally {
  allForfeit.close();
}
console.log("Gamble stepped WASM: nine ports, verified outcomes, clock, refill, and reset pass");
