import assert from "node:assert/strict";
import fs from "node:fs";
import { decode, Kind } from "../shells/web/display-list.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createWillItFallEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_will_it_fall();
assert.equal(task, 1273236717n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 24n, 1n, 0n, 0n, 0n, 0n, 17n), -3n);
const capacity = 65536n;
const pointer = api.nw_frame_alloc(capacity);
assert.ok(pointer > 0n);

const questions = [
  "Does the tower stand or fall?", "Which way does the plank go?", "Where does the ball land?",
  "Which block is the first to topple?", "Where does the ball land the second time?",
];
const seen = new Set();

try {
  const card = TASK_IDS_BY_CATEGORY[3].indexOf("will_it_fall");
  assert.equal(card, 4);
  const hubSize = api.nw_taskhub_write(pointer, capacity, 3n, BigInt(card), 0n, 912n, 684n);
  assert.ok(hubSize > 0n);
  const hub = decode(new Uint8Array(api.memory.buffer, Number(pointer), Number(hubSize)));
  assert.equal(hub.filter(command => command.text === "Will It Fall?").length, 1);
  for (const [rung, margin] of [[1, 32], [4, 28], [8, 22], [12, 16], [16, 10], [20, 4], [25, 2], [30, 2]]) {
    const size = api.nw_falls_options_note(pointer, capacity, BigInt(rung));
    assert.ok(size > 0n);
    const note = new TextDecoder().decode(new Uint8Array(api.memory.buffer, Number(pointer), Number(size)));
    assert.ok(note.startsWith(`Rung ${rung}: towers that stand or fall`));
    assert.ok(note.includes(`Deciding margin ${margin}% of a support.`));
    assert.equal(note.includes("Pivots off the middle"), rung >= 10);
    assert.equal(note.includes("where a ball lands after a bounce"), rung >= 16);
  }
  for (let seed = 0n; seed < 80n && seen.size < questions.length; seed++) {
    const run = api.nw_api_v1_create(task, 1n, 30n, 1n, 0n, 0n, 0n, 0n, seed);
    assert.ok(run > 0n);
    const info = field => Number(api.nw_falls_info(run, BigInt(field)));
    const frame = () => {
      const size = api.nw_api_v1_render(run, pointer, capacity, 1n, 912n, 684n);
      assert.ok(size > 0n);
      return decode(new Uint8Array(api.memory.buffer, Number(pointer), Number(size)));
    };
    let sequence = 0n;
    const event = (kind, code, ms, x = 0n, y = 0n) =>
      api.nw_api_v1_dispatch(run, kind, ms, sequence++, code, 0n, 0n, 0n, x, y, 0n);
    try {
      assert.ok(frame().some(command => command.text === "Press Space to start"));
      assert.equal(event(2n, 1n, 0n), 1n);
      const kind = info(10);
      if (seen.has(kind)) continue;
      seen.add(kind);
      const scene = frame();
      assert.ok(scene.some(command => command.text === questions[kind]));
      assert.equal(info(9), -1);
      const button = scene.find(command => /^1  \S/.test(command.text ?? ""));
      assert.ok(button);
      const coord = (point, extent) => BigInt(Math.round(point * 1e6 / extent));
      assert.equal(event(5n, 0n, 20n, 0n, 0n), 2n);
      const choice = kind === 4 ? 7 : 0;
      if (kind === 0 || kind === 2) {
        assert.equal(event(5n, 0n, 30n, coord(button.a, 912), coord(button.b, 684)), 1n);
      } else {
        assert.equal(event(2n, 12n + BigInt(choice), 30n), 1n);
      }
      assert.equal(info(8), choice);
      assert.equal(info(11), 2830);
      assert.equal(info(6), Number(info(9) === choice));
      const judged = frame();
      assert.ok(judged.some(command => command.text?.startsWith(info(6) ? "Right: " : "No: ")));
      if (kind === 1) {
        const pivot = scene.findIndex(command => command.kind === Kind.POLYGON);
        assert.ok(pivot >= 0);
        assert.ok(scene.slice(pivot + 1, pivot + 4).every(command => command.kind === Kind.POLY_POINT));
      }
      if (kind === 2 || kind === 4) {
        assert.ok(scene.some(command => command.kind === Kind.CIRCLE));
        assert.ok(!scene.some(command => command.kind === Kind.LINE));
        assert.ok(judged.some(command => command.kind === Kind.LINE && command.color === 0x285adcff));
      }
      if (kind === 3) assert.ok(scene.some(command => command.text === "A"));
      assert.equal(api.nw_api_v1_advance(run, 2829n, 0n, sequence++), 2n);
      assert.equal(api.nw_api_v1_advance(run, 2830n, 0n, sequence++), 1n);
      assert.equal(info(0), 3);
      assert.ok(frame().some(command => command.text?.startsWith(`${info(6)} of 1 passed`)));
    } finally {
      assert.equal(api.nw_api_v1_destroy(run), 0n);
    }
  }
  assert.deepEqual([...seen].sort(), [0, 1, 2, 3, 4]);
} finally {
  api.nw_frame_free(pointer);
}
console.log("PASS: Will It Fall? five WASM scenes, key and pointer choices, verdict, and feedback deadline");


// Supply exact verdict pixels so the host receipt and archive paths run in Node.
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
const win = createWillItFallEnvironment(context, { seed: 17, rung: 10, trials: 1 });
try {
  assert.equal(win.n_actions, 8);
  // The Python seeded oracle lands in the second bin.
  const receipt = win.act(1);
  assert.ok(receipt.ok);
  assert.equal(win.act(0).ok, false);
  const judged = win.advance();
  assert.equal(judged.outcome.scalar, 1);
  assert.equal(judged.outcome.receipt_id, receipt.receipt_id);
  assert.ok(win.verify(judged.outcome, judged));
  assert.equal(win.step()[2], true);
  win.reset(17);
  assert.equal(win.step(0)[0].outcome.scalar, -1);
} finally {
  win.close();
}

const clock = createWillItFallEnvironment(context, {
  seed: 17, trials: 2, frameHz: 20, thinkSeconds: 0.1, refillSeconds: 0.05,
});
try {
  // The eighth port has no effect on the rung-one two-choice scene.
  assert.equal(clock.step(7)[0].outcome, undefined);
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
console.log("PASS: Will It Fall? stepped agent receipts, seeded verdict, no-op choice, clock refill, and forfeits");
