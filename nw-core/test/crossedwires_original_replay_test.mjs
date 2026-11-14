// Compare the common-v1 controller against the original Crossed Wires UI and
// exact CrossedWiresEnv port route, including score, adaptation, and timing.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const oracle = JSON.parse(execFileSync("python3", [
  `${root}/test/crossedwires_source_oracle.py`,
], {
  cwd: root,
  encoding: "utf8",
  env: { ...process.env },
  maxBuffer: 8 * 1024 * 1024,
}));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const task = BigInt(exports.nw_api_v1_task_crossed_wires());
const ACTION = Object.freeze({ start: 0n, press: 1n });
const PHASE = Object.freeze({ ready: 0, playing: 1, scored: 2, done: 3 });
const framePtr = Number(exports.nw_frame_alloc(1048576n));
assert.ok(framePtr > 0);

function state(handle) {
  return Array.from({ length: 27 }, (_, field) =>
    Number(exports.nw_api_v1_crossed_wires_info(handle, BigInt(field))));
}

function texts(handle) {
  const length = Number(exports.nw_api_v1_render(handle, BigInt(framePtr),
    1048576n, 0n, 912n, 684n));
  assert.ok(length > 0, `render failed: ${length}`);
  const view = new Uint8Array(instance.exports.memory.buffer, framePtr, length).slice();
  return decode(view).filter(({ kind }) => kind === Kind.TEXT)
    .map(({ text }) => text);
}

function runReplay(replay) {
  const handle = exports.nw_api_v1_create(task, 1n,
    BigInt(replay.level), BigInt(replay.trials), 1n, 1n, 0n, 0n,
    BigInt(replay.seed));
  assert.ok(handle > 0n, "common-v1 should accept source Crossed Wires options");
  let sequence = 0;
  try {
    for (const [index, record] of replay.trace.entries()) {
      const action = record.action === "press" ? ACTION.press : ACTION.start;
      const result = exports.nw_api_v1_dispatch(handle, 1n,
        BigInt(record.now), BigInt(sequence++), action,
        BigInt(record.value), 0n, 0n, 0n, 0n, 0n);
      assert.equal(Number(result), record.result,
        `source ${record.action}(${record.value}) result at trace ${index}`);
      assert.deepEqual(state(handle), record.state,
        `source UI/Env state mismatch after trace ${index}`);
      const message = texts(handle);
      assert.ok(message.some(line => line.includes(record.message)),
        `source message missing at trace ${index}: ${JSON.stringify(record.message)}; got ${JSON.stringify(message)}`);
      assert.ok(!message.some(line => line.toLowerCase().includes("wiring")),
        "the hidden wiring must not enter the display list");
    }
    const final = state(handle);
    assert.equal(final[0], PHASE.done);
    assert.equal(final[22], replay.score.rounds
      ? replay.rounds.reduce((sum, [, reached]) => sum + reached, 0) : 0);
    assert.equal(final[23], replay.rounds
      ? replay.rounds.reduce((sum, [, , targets]) => sum + targets, 0) : 0);
    assert.equal(final[24], replay.score.accuracy);
    assert.equal(final[25], replay.score.best_rung);
    assert.equal(final[26], replay.score.perfect);
    assert.equal(exports.nw_api_v1_crossed_wires_info(handle, 27n), -1n,
      "no public information field may expose the private wire state");
    assert.ok(texts(handle).some(line => line.includes(replay.message)),
      "DONE display must use the source rounds/accuracy/highest-rung summary");
  } finally {
    assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  }
}

assert.equal(task, 2239133075n, "Crossed Wires keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(task)), 1);
for (const replay of oracle.replays) runReplay(replay);
console.log(`crossedwires_original_replay_test: PASS (${oracle.replays.map(r =>
  `${r.trace.length} actions/${r.score.accuracy}%`).join(", ")}; UI keys, Env ports, 800 ms pause, adaptive levels, score and hidden-wiring boundary)`);
