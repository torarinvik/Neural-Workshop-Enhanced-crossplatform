import assert from "node:assert/strict";
import fs from "node:fs";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const { exports: api, instance, createDelayEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_delay();
assert.equal(task, 1322381784n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const create = (rung, trials, adaptive, seed, stepped = 0n) =>
  api.nw_api_v1_create(task, 1n, rung, trials, adaptive, stepped, 0n, 0n, seed);
assert.equal(create(2n, 1n, 1n, 17n), -3n);
assert.equal(create(1n, 2n, 1n, 17n), -3n);
assert.equal(create(1n, 1n, 2n, 17n), -3n);
const custom = create(2n, 2n, 1n, -17n, 1n);
assert.ok(custom > 0n);
assert.equal(api.nw_api_v1_destroy(custom), 0n);

const capacity = 65536n;
const buffer = api.nw_frame_alloc(capacity);
const preview = new TextDecoder();
for (const [rung, description] of [
  [1, "every wait three seconds, shown"],
  [4, "hidden waits of two to six seconds"],
  [7, "mostly short waits, some endless"],
  [10, "every offer different, all shown"],
  [13, "hidden waits that change kind halfway"],
  [16, "three in ten large rewards never come"],
  [20, "kinds mixed and switching"],
  [25, "kinds mixed and switching"],
  [30, "kinds mixed and switching"],
]) {
  const length = api.nw_delay_options_note(buffer, capacity, BigInt(rung));
  assert.ok(length > 0n);
  const bytes = new Uint8Array(instance.exports.memory.buffer, Number(buffer), Number(length));
  assert.equal(preview.decode(bytes), `Rung ${rung}: ${rung < 20 ? 60 : 45} s runs, ${description}.`);
}
let run = create(1n, 1n, 1n, 17n);
let sequence = 0n;
const event = (kind, at, code, x = 0n, y = 0n) =>
  api.nw_api_v1_dispatch(run, kind, BigInt(at), sequence++, code, 0n, 0n, 0n, x, y, 0n);
const pointer = (at, x, y) => event(5n, at, 0n,
  BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)));
const advance = at => api.nw_api_v1_advance(run, BigInt(at), 0n, sequence++);
const info = field => api.nw_api_v1_delay_info(run, BigInt(field));
const text = () => {
  const length = api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n);
  assert.ok(length > 0n);
  return decode(new Uint8Array(instance.exports.memory.buffer, Number(buffer), Number(length)))
    .filter(command => command.kind === Kind.TEXT).map(command => command.text);
};
assert.ok(text().includes("Press Space or click to start"));
assert.equal(pointer(0, 456, 342), 1n);
assert.ok(text().includes("Wait 3.0 s"));
assert.equal(pointer(0, 300, 360), 1n);
assert.equal(info(5), 1n);
assert.equal(advance(999), 2n);
assert.equal(advance(1000), 1n);
assert.equal(event(2n, 1000, 5n), 1n);
assert.equal(advance(2500), 2n);
assert.ok(text().includes("1.5 s"));
assert.ok(text().includes("58 s left"));
assert.equal(advance(3999), 2n);
assert.equal(advance(4000), 1n);
assert.equal(info(5), 9n);
assert.equal(advance(5000), 1n);
assert.equal(pointer(5000, 610, 360), 1n);
assert.equal(event(2n, 5100, 3n), 1n);
assert.equal(info(5), 9n);
assert.equal(advance(5599), 2n);
assert.equal(advance(5600), 1n);
assert.equal(advance(60000), 1n);
assert.equal(api.nw_api_v1_read_state(run, buffer, capacity), 112n);
const state = new DataView(instance.exports.memory.buffer, Number(buffer), 112);
assert.equal(state.getUint32(8, true), Number(task));
assert.deepEqual(Array.from({ length: 12 }, (_, field) => state.getBigInt64(16 + 8 * field, true)),
  [2n, 1n, 1n, 1n, 3n, 9n, 3n, 0n, 0n, 0n, 63000n, 60000n]);
assert.ok(text().includes("9 coins (par 90)"));
assert.equal(advance(62999), 2n);
assert.equal(advance(63000), 1n);
assert.ok(text().includes("0 of 1 passed   highest rung passed 0"));
assert.equal(api.nw_api_v1_destroy(run), 0n);

// Python seed zero at rung 16 opens with an offer that never pays.
run = create(16n, 1n, 0n, 0n);
sequence = 0n;
assert.equal(event(2n, 0, 1n), 1n);
assert.equal(pointer(0, 610, 360), 1n);
assert.ok(text().includes("Wait for it"));
assert.equal(advance(59999), 2n);
assert.equal(info(4), 1n);
assert.equal(info(5), 0n);
assert.equal(advance(60000), 1n);
assert.equal(info(1), 16n);
assert.equal(api.nw_api_v1_destroy(run), 0n);
assert.equal(info(0), -1n);
api.nw_frame_free(buffer);
console.log("PASS: Delay WASM options, pointer and keyboard input, public clock, rewards, never waits, and verdict timing");

const canvas = { width: 96, height: 80 };
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
assert.throws(() => createDelayEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
assert.throws(() => createDelayEnvironment(context, { frameHz: 9 }), /10 frames/);
const env = createDelayEnvironment(context, { seed: 17, trials: 2, frameHz: 16 });
assert.equal(env.n_actions, 2);
assert.ok(env.act(1).ok);
assert.ok(!env.act(0).ok);
for (let tick = 1; tick < 960; tick++) assert.equal(env.advance().outcome, undefined);
const verdict = env.advance();
assert.equal(verdict.outcome.scalar, -1);
assert.ok(env.verify(verdict.outcome, verdict));
assert.equal(env.advance().done, false);
assert.equal(env.accounting.snapshot().logical_trials, 1);
assert.ok(env.act(0).ok);
assert.equal(env.reset(17).frame_seq, 1);
env.close();

const neutral = createDelayEnvironment(context, { frameHz: 16, neutralOutcomes: true, runtimePorts: 4 });
assert.ok(neutral.act(3).ok);
const quiet = neutral.advance();
assert.equal(quiet.outcome.scalar, 0);
assert.ok(neutral.verify(quiet.outcome, quiet));
neutral.close();
console.log("PASS: stepped Delay clock, receipts, sparse verdict, reset, and neutral outcome");
