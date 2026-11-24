import assert from "node:assert/strict";
import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createDispatchEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_dispatch();
assert.equal(task, 2857709163n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 7n, 1n, 0n, 0n, 0n, 0n, 17n), -3n);

const capacity = 1048576n;
const buffer = api.nw_frame_alloc(capacity);
const decoder = new TextDecoder();
function view(length) {
  assert.ok(length > 0n && length <= capacity, `invalid frame length ${length}`);
  return new Uint8Array(api.memory.buffer, Number(buffer), Number(length));
}

const run = api.nw_api_v1_create(task, 1n, 8n, 1n, 0n, 0n, 0n, 0n, 17n);
assert.ok(run > 0n);
let sequence = 0n;
const info = field => api.nw_api_v1_dispatch_info(run, BigInt(field));
const labels = (dark = 0n) => decode(view(api.nw_api_v1_render(run, buffer, capacity, dark, 912n, 684n)))
  .filter(command => command.text !== undefined);
const advance = (now, elapsed) => api.nw_api_v1_advance(run, BigInt(now), BigInt(elapsed), sequence++);
const event = (kind, code, time, modifiers = 0n, x = 0, y = 0) =>
  api.nw_api_v1_dispatch(run, kind, BigInt(time), sequence++, code, 0n, modifiers, 0n,
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);

try {
  const decisions = TASK_IDS_BY_CATEGORY.findIndex(ids => ids.includes("dispatch"));
  assert.deepEqual(TASK_IDS_BY_CATEGORY[decisions], ["sonar", "dispatch", "gamble", "bluff", "explore_exploit", "firebreak", "crossroads", "triage", "dam_keeper"]);
  const hub = decode(view(api.nw_taskhub_write(buffer, capacity, BigInt(decisions), 1n, 0n, 912n, 684n)));
  assert.ok(hub.some(command => command.text === "Dispatch"));
  assert.match(decoder.decode(view(api.nw_dispatch_options_note(buffer, capacity, 8n))),
    /^Rung 8: 3 crews, bursts of up to 3\..*12 seconds at a station for a refit/);

  assert.ok(labels().some(command => command.text === "Press Space to start"));
  assert.equal(event(5n, 0n, 0, 0n, 456, 350), 2n);
  assert.equal(event(2n, 1n, 0), 1n);
  assert.ok(labels(1n).some(command => command.text === "Keep the damage to 64 or less"));

  // The source round's crew one refits, and crew two drives to L and then to A.
  // This is the same scripted route exercised through SDL.
  let time = 0;
  for (let tick = 1; tick < 600 && info(0) === 1n; tick++) {
    time = tick * 250;
    if (tick === 1) {
      assert.equal(event(2n, 12n, time), 1n);
      assert.equal(info(4), 0n);
    } else if (tick === 2) {
      assert.equal(event(2n, 43n, time, 1n), 1n);
      assert.equal(info(4), -1n);
    } else if (tick === 3) {
      assert.equal(event(5n, 0n, time, 0n, 564.92, 295.7), 1n);
      assert.equal(info(4), 1n);
    } else if (tick === 4) {
      assert.equal(event(5n, 0n, time, 0n, 456, 482.42), 1n);
      assert.equal(info(4), -1n);
    } else if (tick === 16) {
      assert.equal(event(2n, 13n, time), 1n);
    } else if (tick === 17) {
      assert.equal(event(2n, 35n, time), 1n);
    }
    assert.equal(advance(time, 250), 1n);
    if (tick === 52) assert.ok(labels().some(command => command.text.endsWith("refits 1/3")));
  }
  assert.equal(info(0), 2n);
  assert.equal(info(7), 224n);
  assert.ok(labels().some(command => command.text === "Damage 224 against a par of 64: 1 saved, 5 lost" &&
    command.color === 0xff4040ff));
  const state = view(api.nw_api_v1_read_state(run, buffer, capacity));
  const packet = new DataView(state.buffer, state.byteOffset, state.byteLength);
  assert.equal(state.byteLength, 112);
  assert.equal(packet.getUint32(12, true), 12);
  for (let field = 0; field < 12; field++) assert.equal(packet.getBigInt64(16 + field * 8, true), info(field));
  assert.equal(advance(time + 2199, 2199), 2n);
  assert.equal(advance(time + 2200, 1), 1n);
  assert.ok(labels().some(command => command.text === "0 of 1 rounds under par   highest rung passed 0"));
  assert.equal(event(2n, 1n, time + 2201), 1n);
  assert.equal(info(6), 0n);
} finally {
  assert.equal(api.nw_api_v1_destroy(run), 0n);
  assert.equal(api.nw_api_v1_dispatch_info(run, 0n), -1n);
  api.nw_frame_free(buffer);
}
console.log("Dispatch WASM: hub, options, timed orders, refit, Python score, feedback, and restart pass");

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

const oracle = fileURLToPath(new URL("./dispatch_agent_oracle.py", import.meta.url));
const fixture = JSON.parse(execFileSync(process.env.PYTHON_BIN ?? "python3", [oracle], { encoding: "utf8" }));
assert.throws(() => createDispatchEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
for (const [mode, ticks] of Object.entries(fixture)) {
  const coached = mode === "coached";
  const env = createDispatchEnvironment(context, {
    seed: 17, rung: 8, trials: 1, adaptive: false, frameHz: 10, neutralOutcomes: coached,
  });
  try {
    assert.equal(env.n_actions, 18);
    for (const [port, scalar, words] of ticks) {
      const receipt = env.act(port);
      assert.ok(receipt.ok);
      assert.equal(env.act(port).ok, false);
      const frame = env.advance();
      if (words) assert.ok(context.labels.includes(words), words);
      if (coached || scalar !== 0) {
        assert.equal(frame.outcome.scalar, scalar);
        assert.equal(frame.outcome.receipt_id, receipt.receipt_id);
        assert.ok(env.verify(frame.outcome, frame));
      } else {
        assert.equal(frame.outcome, undefined);
        assert.ok(!context.labels.includes("Saved one") && !context.labels.includes("Lost one"));
      }
      assert.equal(frame.done, false);
    }
    const done = env.advance();
    assert.ok(done.done);
    assert.equal(done.outcome, undefined);
    assert.equal(env.reset(17).done, false);
  } finally {
    env.close();
  }
}
const idle = createDispatchEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 10 });
try {
  let judged;
  for (let tick = 0; tick < 1600 && !judged; tick++) {
    const frame = idle.advance();
    if (frame.outcome) judged = frame;
  }
  assert.equal(judged?.outcome.scalar, -1);
  assert.ok(idle.verify(judged.outcome, judged));
  assert.ok(idle.advance().done);
} finally {
  idle.close();
}
console.log("Dispatch stepped WASM: clocked input, Python sparse and coached replays, and verified receipts pass");
