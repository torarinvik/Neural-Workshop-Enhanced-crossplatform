import assert from "node:assert/strict";
import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createDamKeeperEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_dam_keeper();
assert.equal(task, 2780310580n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(api.nw_api_v1_create(task, 1n, 3n, 1n, 1n, 0n, 0n, 0n, 222n), -3n);
assert.equal(api.nw_api_v1_create(task, 1n, 1n, 2n, 1n, 0n, 0n, 0n, 222n), -3n);

const capacity = 65536n;
const pointer = api.nw_frame_alloc(capacity);
const buffer = length => {
  assert.ok(length > 0n && length <= capacity, `frame length ${length}`);
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
};
try {
  const category = TASK_IDS_BY_CATEGORY.findIndex(ids => ids.includes("dam_keeper"));
  const selected = TASK_IDS_BY_CATEGORY[category].indexOf("dam_keeper");
  const hub = decode(buffer(api.nw_taskhub_write(pointer, capacity, BigInt(category), BigInt(selected), 0n, 912n, 684n)));
  assert.ok(hub.some(command => command.text === "Dam Keeper"));
  assert.equal(new TextDecoder().decode(buffer(api.nw_dam_keeper_options_note(pointer, capacity, 16n))),
    "Rung 16: 3 dams, 3 storm(s).  Gates are slow to move.  No forecast.");

  const run = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 222n);
  assert.ok(run > 0n);
  const info = field => api.nw_api_v1_dam_keeper_info(run, BigInt(field));
  const frame = () => decode(buffer(api.nw_api_v1_render(run, pointer, capacity, 1n, 912n, 684n)));
  let sequence = 0n;
  const input = (kind, code, time, x = 0, y = 0, flags = 0n) => api.nw_api_v1_dispatch(
    run, kind, time, sequence++, code, 0n, 0n, flags,
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
  const advance = time => api.nw_api_v1_advance(run, time, 0n, sequence++);
  try {
    assert.ok(frame().some(command => command.text === "Press Space or click to start"));
    assert.equal(input(2n, 1n, 0n), 1n);
    assert.equal(info(5), 2n);
    assert.equal(input(2n, 26n, 1n, 0, 0, 1n), 2n);
    assert.equal(input(2n, 26n, 2n), 1n);
    const scale = 857.28 / 154;
    const gateX = 27.36 + (48 + 30) * scale;
    const gateY = 179 + 42 * scale;
    assert.equal(input(5n, 0n, 3n, gateX, gateY - 4), 1n);
    assert.equal(input(5n, 0n, 4n, 100, 100), 2n);
    assert.equal(advance(1000n), 1n);
    assert.equal(info(4), 100n, "logical clock clamps a long frame");
    assert.ok(frame().some(command => command.text === "Make room before the rain; never flood the town"));
    for (let time = 1100n; time <= 92000n && info(0) === 1n; time += 100n) {
      assert.equal(advance(time), 1n);
    }
    assert.equal(info(0), 2n);
    assert.equal(info(6), 2n);
    assert.ok(frame().some(command => /^Dam [12] overtopped$/.test(command.text ?? "")));
    const deadline = info(10);
    assert.equal(advance(deadline - 1n), 2n);
    assert.equal(advance(deadline), 1n);
    assert.equal(info(0), 3n);
    assert.ok(frame().some(command => command.text === "0 of 1 passed   highest rung passed 0"));
    assert.equal(input(5n, 0n, deadline + 1n, 456, 380), 1n);
    assert.equal(info(0), 1n);
  } finally {
    assert.equal(api.nw_api_v1_destroy(run), 0n);
  }
  const oracle = JSON.parse(execFileSync(process.env.PYTHON_BIN || "python3",
    [fileURLToPath(new URL("./damkeeper_agent_oracle.py", import.meta.url))], { encoding: "utf8" }));
  for (const replay of oracle.runs) {
    const agent = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 1n, 0n, 0n, BigInt(oracle.seed));
    assert.ok(agent > 0n);
    try {
      assert.equal(api.nw_dam_keeper_agent_event(agent, NaN, 6n), -10n);
      assert.equal(api.nw_dam_keeper_agent_event(agent, 0, 6n), 1n);
      const ports = new Map(replay.actions);
      let seconds = 0;
      for (let tick = 1; tick <= replay.ticks; tick++) {
        if (ports.has(tick)) {
          // The third dam's ports are no-ops on this two-dam valley.
          const port = ports.get(tick);
          assert.equal(api.nw_dam_keeper_agent_event(agent, seconds, BigInt(port)), port < 4 ? 1n : 2n);
        }
        seconds += 1 / oracle.frameHz;
        assert.equal(api.nw_dam_keeper_agent_event(agent, seconds, -1n), 1n);
        assert.equal(api.nw_api_v1_dam_keeper_info(agent, 0n), tick === replay.ticks ? 2n : 1n);
      }
      const verdict = decode(buffer(api.nw_api_v1_render(agent, pointer, capacity, 0n, 912n, 684n)));
      assert.ok(verdict.some(command => command.text === replay.verdict));
      assert.equal(api.nw_dam_keeper_agent_event(agent, seconds + 1 / oracle.frameHz, -1n), 1n);
      assert.equal(api.nw_api_v1_dam_keeper_info(agent, 0n), 3n);
    } finally {
      assert.equal(api.nw_api_v1_destroy(agent), 0n);
    }
  }

  // A recording canvas leaves the WASM draw list and receipt logic intact
  // while supplying only the verdict glyph colours for the pixel verifier.
  const canvas = { width: 228, height: 171 };
  const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
  const context = {
    canvas,
    save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
    strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, moveTo() {}, lineTo() {}, closePath() {},
    clearRect() { pixels.fill(0); },
    fillRect() {},
    fillText(text) {
      if (text === oracle.runs[0].verdict && this.fillStyle === "rgba(255,64,64,1.000)") {
        pixels.set([255, 64, 64, 255], pixels.length - 4);
        pixels.set([255, 64, 64, 255], pixels.length - 4 - canvas.width * 4);
      }
    },
    getImageData() { return { data: pixels }; },
  };
  assert.throws(() => createDamKeeperEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
  const env = createDamKeeperEnvironment(context, { seed: oracle.seed, trials: 1, frameHz: oracle.frameHz });
  try {
    assert.equal(env.n_actions, 6);
    assert.equal(env.act(4).ok, true);
    assert.equal(env.act(0).ok, false);
    let frame;
    for (let tick = 1; tick <= oracle.runs[0].ticks; tick++) {
      frame = env.advance();
      assert.equal(frame.done, false);
      if (tick < oracle.runs[0].ticks) assert.equal(frame.outcome, undefined);
    }
    assert.equal(frame.outcome.scalar, -1);
    assert.ok(env.verify(frame.outcome, frame));
    assert.equal(env.advance().done, true);
    assert.equal(env.reset(oracle.seed).done, false);
  } finally {
    env.close();
  }
} finally {
  api.nw_frame_free(pointer);
}

console.log("dam_keeper_wasm_smoke: PASS (interactive route, Python stepped replays, receipt verification, and cleanup)");
