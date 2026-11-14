// Compare the live controller with the original UI and CrosswordEnv routes.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const task = BigInt(exports.nw_api_v1_task_crossword());
function runReplay(slips, reverse = false) {
  const oracle = JSON.parse(execFileSync("python3", [`${root}/test/crossword_source_oracle.py`], {
    cwd: root, encoding: "utf8", env: { ...process.env, NW_CROSSWORD_SLIPS: String(slips), NW_CROSSWORD_REVERSE: reverse ? "1" : "0" },
    maxBuffer: 32 * 1024 * 1024,
  }));
  const handle = exports.nw_api_v1_create(task, 1n, 2n, 1n, 1n, 1n, 0n, 0n, 17n);
  assert.ok(handle > 0n);
  const index = new TextEncoder().encode(oracle.index);
  const input = Number(exports.nw_frame_alloc(BigInt(index.length)));
  assert.ok(input > 0);
  new Uint8Array(instance.exports.memory.buffer, input, index.length).set(index);
  assert.equal(exports.nw_api_v1_crossword_set_lexicon(handle, BigInt(input), BigInt(index.length)), 0n);
  exports.nw_frame_free(BigInt(input));
  const frame = Number(exports.nw_frame_alloc(1048576n));
  assert.ok(frame > 0);
  try {
    for (const [sequence, record] of oracle.trace.entries()) {
      const result = exports.nw_api_v1_dispatch(handle, 1n, BigInt(record.now), BigInt(sequence),
        BigInt(record.action), BigInt(record.value), 0n, 0n, 0n, 0n, 0n);
      assert.equal(Number(result), record.result, `action result at ${sequence} (${slips} slips)`);
      const state = Array.from({ length: 20 }, (_, field) =>
        Number(exports.nw_api_v1_crossword_info(handle, BigInt(field))));
      assert.deepEqual(state, record.state, `source state at action ${sequence} (${slips} slips)`);
      const cells = record.cells.map((_, at) => Array.from({ length: 3 }, (_, field) =>
        Number(exports.nw_api_v1_crossword_value(handle, BigInt(field), BigInt(at)))));
      assert.deepEqual(cells, record.cells, `source grid at action ${sequence} (${slips} slips)`);
      const length = Number(exports.nw_api_v1_render(handle, BigInt(frame), 1048576n, 0n, 912n, 684n));
      assert.ok(length > 0);
      const bytes = new Uint8Array(instance.exports.memory.buffer, frame, length).slice();
      const text = decode(bytes).filter(command => command.kind === Kind.TEXT).map(command => command.text);
      assert.ok(text.some(line => line.includes(record.message)),
        `source message at ${sequence}: ${JSON.stringify(record.message)}; got ${JSON.stringify(text)}`);
      if (record.clue) assert.ok(text.includes(record.clue), `source clue at ${sequence}: ${record.clue}`);
    }
  } finally {
    exports.nw_frame_free(BigInt(frame));
    assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  }
  return oracle.trace.length;
}
const counts = [runReplay(1), runReplay(5), runReplay(1, true)];
console.log(`crossword_original_replay_test: PASS (${counts.join(" + ")} UI/Env actions; sorted/unsorted generation, blocks, clues, edits, adaptive stay/drop, score and restart)`);
