import assert from "node:assert/strict";
import fs from "node:fs";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_signals();
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const read = length => new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
const frame = run => decode(read(api.nw_api_v1_render(run, pointer, capacity, 0n, 912n, 684n)));
assert.equal(task, 3284569614n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 13n, 1n, 1n, 0n, 0n, 0n, 17n), -3n);

try {
  const category = TASK_IDS_BY_CATEGORY[4];
  const selected = category.indexOf("signals");
  assert.equal(category[selected - 1], "verbal_reasoning");
  const hub = decode(read(api.nw_taskhub_write(pointer, capacity, 4n, BigInt(selected), 0n, 912n, 684n)));
  assert.equal(hub.filter(command => command.text === "Signals").length, 1);
  assert.equal(new TextDecoder().decode(read(api.nw_signals_options_note(pointer, capacity, 25n))),
    "Rung 25: 11 exchanges, 8 objects, you take turns; glyphs name colours and shapes, 2 to a signal.  The partner changes its code partway.  You must beat the reference.");

  const run = api.nw_api_v1_create(task, 1n, 12n, 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(run > 0n);
  let sequence = 0n;
  const dispatch = (kind, code, time, x = 0, y = 0) => api.nw_api_v1_dispatch(run, BigInt(kind), BigInt(time),
    sequence++, BigInt(code), 0n, 0n, 0n, BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
  const info = field => api.nw_api_v1_signals_info(run, BigInt(field));
  try {
    assert.ok(frame(run).some(command => command.text === "Press Space or click to start"));
    assert.equal(dispatch(2, 1, 0), 1n);
    assert.equal(info(11), 0n);
    const initial = frame(run);
    assert.ok(initial.some(command => command.text === "Partner says"));
    assert.ok(initial.some(command => command.kind === Kind.CIRCLE && command.color === 0x32aa50ff));
    assert.equal(dispatch(5, 0, 50, 50, 210), 2n);
    assert.equal(info(4), 0n);
    assert.equal(dispatch(5, 0, 100, 120, 350), 1n);
    assert.equal(info(4), 1n);
    assert.equal(info(11), 1n);
    const speaking = frame(run);
    assert.ok(speaking.some(command => command.text === "You say"));
    assert.ok(speaking.some(command => command.kind === Kind.BOX && command.e === 4));
    assert.ok(speaking.some(command => command.text === "right"));

    // Python level 12, session seed 17. Use a glyph click for the first
    // half-message and typed action ports for the rest.
    assert.equal(dispatch(5, 0, 150, 300, 220), 1n);
    assert.equal(info(4), 1n);
    assert.equal(dispatch(1, 15, 200), 1n);
    const exchanges = [[0], [1, 2], [1], [3, 7], [0], [1, 6], [3], [4, 7],
      [3], [4, 6], [3], [4, 2], [3], [1, 0]];
    for (const [at, ports] of exchanges.entries()) {
      for (const port of ports) {
        if (at % 2 === 0) assert.equal(dispatch(2, 12 + port, 250), 1n);
        else assert.equal(dispatch(1, 8 + port, 250), 1n);
      }
    }
    assert.equal(info(0), 2n);
    assert.equal(info(5), 1n);
    assert.equal(info(9), 16n);
    assert.equal(info(1), 13n);
    const verdict = frame(run);
    assert.ok(verdict.some(command => command.text === "16 of 16 exchanges understood (par 11.1)" &&
      command.color === 0x40ff40ff));
    assert.equal(verdict.filter(command => command.text === "right").length, 6);
    assert.equal(api.nw_api_v1_advance(run, 3049n, 0n, sequence++), 2n);
    assert.equal(api.nw_api_v1_advance(run, 3050n, 0n, sequence++), 1n);
    assert.equal(info(0), 3n);
  } finally {
    assert.equal(api.nw_api_v1_destroy(run), 0n);
  }
} finally {
  api.nw_frame_free(pointer);
}
console.log("PASS: Signals WASM hub, seeded visual roles, pointer and key controls, history, adaptive score, and feedback");

const canvas = { width: 320, height: 240 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  fillRect() {}, strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {},
  moveTo() {}, lineTo() {}, closePath() {},
  clearRect() { pixels.fill(0); },
  fillText() {
    const color = this.fillStyle === "rgba(64,255,64,1.000)" ? [64, 255, 64, 255]
      : this.fillStyle === "rgba(255,64,64,1.000)" ? [255, 64, 64, 255] : null;
    if (color) {
      pixels.set(color, pixels.length - 4);
      pixels.set(color, pixels.length - 4 - canvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};
const runtime = await instantiateElisa(bytes, { warn: false });
const agent = runtime.createSignalsEnvironment(context, { seed: 17, rung: 12, trials: 1 });
try {
  assert.equal(agent.n_actions, 16);
  const ports = [0, 11, 15, 0, 9, 10, 1, 11, 15, 0, 9, 14,
    3, 12, 15, 3, 12, 14, 3, 12, 10, 3, 9, 8];
  for (const port of ports.slice(0, -1)) assert.equal(agent.step(port)[0].outcome, undefined);
  const receipt = agent.act(ports.at(-1));
  assert.ok(receipt.ok);
  assert.equal(agent.act(0).ok, false);
  const verdict = agent.advance();
  assert.equal(verdict.outcome.scalar, 1);
  assert.equal(verdict.outcome.receipt_id, receipt.receipt_id);
  assert.ok(agent.verify(verdict.outcome, verdict));
  assert.equal(agent.step()[2], true);
} finally {
  agent.close();
}

const clock = runtime.createSignalsEnvironment(context, {
  seed: 17, trials: 2, frameHz: 20, thinkSeconds: 0.1, refillSeconds: 0.05,
});
try {
  assert.equal(clock.step(8)[0].outcome, undefined);
  const flag = clock.step()[0];
  assert.equal(flag.outcome.scalar, -1);
  assert.ok(clock.verify(flag.outcome, flag));
  assert.equal(clock.forfeits, 1);
  assert.equal(clock.step()[2], false);
  assert.equal(clock.think_left, 0.05);
  assert.equal(clock.step()[0].outcome.scalar, -1);
  assert.equal(clock.step()[2], true);
  assert.equal(clock.forfeits, 2);
} finally {
  clock.close();
}
console.log("PASS: stepped Signals WASM receipts, verified verdicts, forfeits, and refill");
