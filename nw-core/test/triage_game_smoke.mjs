import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, instance, createTriageEnvironment } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const task = api.nw_api_v1_task_triage();
assert.equal(task, 166983937n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);

const create = (rung, rounds = 1n, adaptive = 1n) =>
  api.nw_api_v1_create(task, 1n, rung, rounds, adaptive, 0n, 0n, 0n, 17n);
assert.equal(create(2n), -3n);
assert.equal(create(1n, 2n), -3n);
assert.equal(create(1n, 1n, 2n), -3n);

const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const decoder = new TextDecoder();
for (const [rung, cards, shortest, longest, share] of [
  [1, 2, 3, 3, 100], [3, 2, 3, 4, 100], [5, 3, 3, 5, 100],
  [8, 4, 4, 6, 95], [12, 5, 4, 8, 75], [16, 7, 5, 9, 55],
  [20, 8, 6, 9, 35], [21, 8, 6, 9, 30], [25, 8, 7, 9, 30], [30, 8, 7, 9, 30],
]) {
  let expected = `Rung ${rung}: ${cards} cards of ${shortest} to ${longest} digits; the moves cover about ${share}% of the work.`;
  if (rung >= 8) {
    expected += "  With pay that does not follow cost";
    if (rung >= 12) expected += ", face-down cards that cost a move to turn";
    expected += ".";
  }
  if (rung > 20) expected += "  You must beat the reference.";
  const length = api.nw_triage_options_note(buffer, capacity, BigInt(rung));
  assert.equal(length, BigInt(expected.length));
  assert.equal(decoder.decode(new Uint8Array(instance.exports.memory.buffer, Number(buffer), Number(length))), expected);
}
assert.equal(api.nw_triage_options_note(buffer, capacity, 2n), -3n);
assert.ok(api.nw_triage_options_note(buffer, 1n, 1n) < 0n);

let run = create(1n);
let time = 100n;
let sequence = 0n;
const event = (kind, code, x = 0n, y = 0n) =>
  api.nw_api_v1_dispatch(run, kind, time++, sequence++, code, 0n, 0n, 0n, x, y, 0n);
const pointer = (x, y) => event(5n, 0n,
  BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)));
const info = field => api.nw_api_v1_triage_info(run, BigInt(field));
const state = () => {
  const length = api.nw_api_v1_read_state(run, buffer, capacity);
  assert.equal(length, 112n);
  const view = new DataView(instance.exports.memory.buffer, Number(buffer), Number(length));
  assert.equal(view.getUint32(8, true), Number(task));
  assert.equal(view.getUint32(12, true), 12);
  return Array.from({ length: 12 }, (_, field) => view.getBigInt64(16 + 8 * field, true));
};
const frame = (black = 0n) => {
  const length = api.nw_api_v1_render(run, buffer, capacity, black, 912n, 684n);
  assert.ok(length > 0n);
  return decode(new Uint8Array(instance.exports.memory.buffer, Number(buffer), Number(length)));
};

const text = () => frame().filter(command => command.kind === Kind.TEXT).map(command => command.text);

// Python seed 17 at rung 1 deals (3,1,2) for 4 points and (1,3,2) for 1.
assert.equal(event(2n, 1n), 1n);
assert.deepEqual(state().slice(0, 8), [1n, 1n, 1n, 1n, 4n, 0n, 0n, -1n]);
assert.ok(text().includes("Earn 2.5 or more with 4 moves"));
assert.equal(pointer(456, 20), 2n);
assert.equal(event(2n, 12n), 1n);
// Python polish.machine draws a blue header, a recessed screen, and a
// selected ring. Every rounded polygon must include all its points.
for (const [black, screenColor] of [[0n, 0xdee2e7ff], [1n, 0x1b1e27ff]]) {
  const commands = frame(black);
  const polygons = commands.filter(command => command.kind === Kind.POLYGON);
  assert.ok(polygons.some(command => command.color === 0x5676c4ff));
  assert.ok(polygons.some(command => command.color === screenColor));
  assert.ok(polygons.some(command => command.color === 0x285adcff));
  assert.equal(commands.filter(command => command.kind === Kind.POLY_POINT).length,
    polygons.reduce((sum, command) => sum + command.len, 0));
}
assert.equal(pointer(390, 293), 1n);
assert.equal(pointer(525, 293), 1n);
assert.equal(pointer(640, 500), 1n);
assert.equal(pointer(525, 293), 1n);
assert.deepEqual(state().slice(0, 10), [2n, 2n, 1n, 1n, 4n, 3n, 5n, -1n, 1n, 1n]);
assert.ok(frame().some(command => command.kind === Kind.POLYGON && command.color === 0x3caa5aff));
assert.equal(info(12), 3n);
const deadline = info(10);
assert.equal(deadline, time - 1n + 2500n);
assert.equal(pointer(100, 535), 2n);
assert.equal(api.nw_api_v1_advance(run, deadline - 1n, 0n, sequence++), 2n);
assert.equal(api.nw_api_v1_advance(run, deadline, 0n, sequence++), 1n);
assert.ok(text().includes("1 of 1 passed   highest rung passed 1"));
assert.equal(api.nw_api_v1_destroy(run), 0n);

run = create(12n, 1n, 0n);
assert.equal(pointer(456, 342), 1n);
assert.ok(text().includes("6 digits, face down"));
assert.ok(!text().includes("2 5 1 4 3 6"));
assert.equal(info(11), 0n);
assert.equal(pointer(100, 535), 1n);
assert.equal(info(5), 1n);
assert.equal(info(11), 1n);
assert.ok(text().includes("2 5 1 4 3 6"));
assert.equal(event(2n, 2n), 1n);
assert.equal(info(1), 12n);
assert.ok(text().some(line => line.startsWith("Earned 0 against a par of")));
assert.equal(api.nw_api_v1_destroy(run), 0n);
assert.equal(info(0), -1n);
api.nw_frame_free(buffer);
console.log("PASS: Triage WASM options, pointer and keyboard input, hidden rows, payout, deadline, and cleanup");

const canvas = { width: 912, height: 684 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  fillRect() {}, strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {},
  moveTo() {}, lineTo() {}, closePath() {},
  clearRect() { pixels.fill(0); },
  fillText() {
    const colors = {
      "rgba(64,255,64,1.000)": [64, 255, 64, 255],
      "rgba(255,64,64,1.000)": [255, 64, 64, 255],
    };
    const color = colors[this.fillStyle];
    if (color) {
      pixels.set(color, pixels.length - 4);
      pixels.set(color, pixels.length - 4 - canvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};
const environment = createTriageEnvironment(context, { seed: 17, trials: 1 });
assert.equal(environment.n_actions, 17);
for (const port of [0, 8, 9, 1]) assert.equal(environment.step(port)[0].outcome, undefined);
const finalReceipt = environment.act(9);
assert.ok(finalReceipt.ok);
assert.equal(environment.act(16).ok, false);
const verdict = environment.advance();
assert.equal(verdict.outcome.scalar, 1);
assert.equal(verdict.outcome.receipt_id, finalReceipt.receipt_id);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
assert.equal(environment.reset(17).frame_seq, 1);
environment.close();

const clock = createTriageEnvironment(context, {
  seed: 17, trials: 3, frameHz: 20, thinkSeconds: 0.1, refillSeconds: 0.05,
});
assert.equal(clock.step()[0].outcome, undefined);
const flag = clock.step()[0];
assert.equal(flag.outcome.scalar, -1);
assert.ok(clock.verify(flag.outcome, flag));
assert.equal(clock.forfeits, 1);
assert.equal(clock.think_left, 0);
assert.equal(clock.step()[2], false);
assert.equal(clock.think_left, 0.05);
assert.equal(clock.step()[0].outcome.scalar, -1);
assert.equal(clock.forfeits, 2);
clock.close();
console.log("PASS: stepped Triage receipts, sparse verdicts, think forfeits, refill, and seeded reset");

const neutral = createTriageEnvironment(context, { seed: 17, trials: 1, neutralOutcomes: true, runtimePorts: 20 });
const extra = neutral.act([99, 19]);
assert.ok(extra.ok);
const quiet = neutral.advance();
assert.equal(quiet.outcome.scalar, 0);
assert.equal(quiet.outcome.receipt_id, extra.receipt_id);
assert.ok(neutral.verify(quiet.outcome, quiet));
const changed = structuredClone(quiet);
changed.rgba[0] ^= 1;
assert.equal(neutral.verify(quiet.outcome, changed), false);
neutral.close();

assert.equal(api.nw_api_v1_create(task, 1n, 4n, 2n, 1n, 0n, 0n, 0n, 17n), -3n);
assert.equal(api.nw_api_v1_create(task, 1n, 4n, 2n, 1n, 2n, 0n, 0n, 17n), -3n);
const drawn = [];
const dialContext = { ...context, fillText(text) { drawn.push(text); context.fillText.call(this, text); } };
const dials = createTriageEnvironment(dialContext, { seed: "-17", rung: " 4 ", trials: 2.9, adaptive: false });
assert.ok(drawn.some(text => text.startsWith("rung 4   1/2")));
const negativeSeedFrame = [...drawn];
drawn.length = 0;
dials.reset(17);
assert.deepEqual(drawn, negativeSeedFrame);
assert.equal(dials.step(16)[0].outcome.scalar, -1);
drawn.length = 0;
assert.equal(dials.step()[2], false);
assert.ok(drawn.some(text => text.startsWith("rung 4   2/2")));
assert.equal(dials.step(16)[0].outcome.scalar, -1);
assert.equal(dials.step()[2], true);
dials.close();

for (const trials of [0, -2]) {
  const empty = createTriageEnvironment(context, { trials });
  assert.equal(empty.observe().done, true);
  assert.equal(empty.act(0).ok, false);
  assert.deepEqual(empty.step()[1].map(event => event.type), ["run_end"]);
  assert.deepEqual(empty.step()[1], []);
  empty.close();
}
drawn.length = 0;
const clamped = createTriageEnvironment(dialContext, { rung: -5, trials: 1 });
assert.ok(drawn.some(text => text.startsWith("rung 1   1/1")));
clamped.close();
assert.throws(() => createTriageEnvironment(context, { rung: "4.5" }), /must be an integer/);
assert.throws(() => createTriageEnvironment(context, { trials: 2n ** 63n }), /signed 64-bit range/);
console.log("PASS: Triage environment dials, signed seeds, and empty-run completion");
