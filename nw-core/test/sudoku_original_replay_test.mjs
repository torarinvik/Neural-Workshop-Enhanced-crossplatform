// Differential replay of the original Sudoku UI/environment against the
// source-backed common-v1 controller. The Python oracle exercises the exact
// SudokuEnv.drive port mapping and Sudoku UI methods; this side applies those
// same ports through the browser-facing semantic action API.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const workspaceRoot = fileURLToPath(new URL("../../", import.meta.url));
const oraclePath = `${root}/test/sudoku_source_oracle.py`;
const sourceRoot = `${workspaceRoot}/original-neural-workshop-enhanced`;
const oracle = JSON.parse(execFileSync("python3", [oraclePath], {
  cwd: root,
  encoding: "utf8",
  env: { ...process.env, NW_HEADLESS: "1", PYTHONPATH: sourceRoot },
  maxBuffer: 8 * 1024 * 1024,
}));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const task = BigInt(exports.nw_api_v1_task_sudoku());
const handle = exports.nw_api_v1_create(task, 1n,
  BigInt(oracle.level), BigInt(oracle.total_trials), 1n, 1n, 0n, 0n,
  BigInt(oracle.seed));
assert.ok(handle > 0n, "common-v1 should accept source Sudoku defaults");

const ACTION = Object.freeze({
  start: 0n, up: 1n, down: 2n, left: 3n, right: 4n,
  write: 5n, erase: 6n, pencil: 7n,
});
const INFO = Object.freeze({
  phase: 0, rung: 1, trial: 2, totalTrials: 3, size: 5, cursor: 7,
  pencil: 8, mistakes: 9, verdict: 10, blanks: 13,
  showClashes: 11, hasPuzzle: 14,
});
const VALUE = Object.freeze({ given: 0n, solution: 1n, filled: 2n, marks: 3n });
const STATUS_ACCEPTED = 1n;
let timestamp = 100;
let sequence = 0;

function info(field) {
  return Number(exports.nw_api_v1_sudoku_info(handle, BigInt(field)));
}

function state() {
  return [INFO.phase, INFO.rung, INFO.trial, INFO.totalTrials, INFO.size,
    INFO.cursor, INFO.pencil, INFO.mistakes, INFO.verdict, INFO.blanks,
    INFO.showClashes, INFO.hasPuzzle].map(info);
}

function values(field, cells) {
  return Array.from({ length: cells }, (_, cell) =>
    Number(exports.nw_api_v1_sudoku_value(handle, field, BigInt(cell))));
}

function action(code, value = 0n) {
  return exports.nw_api_v1_dispatch(handle, 1n, BigInt(timestamp++),
    BigInt(sequence++), code, value, 0n, 0n, 0n, 0n, 0n);
}

function applySourcePort(port) {
  if (port === 0) return action(ACTION.up);
  if (port === 1) return action(ACTION.down);
  if (port === 2) return action(ACTION.left);
  if (port === 3) return action(ACTION.right);
  if (port < 20) return action(ACTION.write, BigInt(port - 3));
  if (port === 20) return action(ACTION.erase);
  if (port === 21) return action(ACTION.pencil);
  throw new Error(`unexpected SudokuEnv source port ${port}`);
}

try {
  assert.equal(task, 4211466488n, "Sudoku keeps its stable task ID");
  assert.equal(action(ACTION.start), STATUS_ACCEPTED);
  assert.deepEqual(state(), oracle.initial, "the initial source deal diverged");
  const cells = oracle.givens.length;
  assert.deepEqual(values(VALUE.given, cells), oracle.givens,
    "source givens diverged");
  assert.deepEqual(values(VALUE.solution, cells), oracle.solution,
    "source solution diverged");
  assert.ok(oracle.wrong_clashes.length >= 2,
    "the source replay must exercise a duplicate row/column/box entry");

  for (const [index, record] of oracle.trace.entries()) {
    assert.equal(applySourcePort(record.port), STATUS_ACCEPTED,
      `source port ${record.port} rejected at trace index ${index}`);
    assert.deepEqual(state(), record.state,
      `controller metadata diverged after source port ${record.port} at trace index ${index}`);
    assert.deepEqual(values(VALUE.filled, cells), record.filled,
      `filled grid diverged after source port ${record.port} at trace index ${index}`);
    assert.deepEqual(values(VALUE.marks, cells), record.marks,
      `pencil mask diverged after source port ${record.port} at trace index ${index}`);
  }

  const duplicate = oracle.trace[oracle.wrong_clash_trace_index];
  const size = Math.sqrt(cells);
  const controllerClashes = new Set();
  for (let first = 0; first < cells; first++) {
    const value = duplicate.filled[first];
    if (value === 0) continue;
    for (let second = first + 1; second < cells; second++) {
      const sameRow = Math.floor(first / size) === Math.floor(second / size);
      const sameColumn = first % size === second % size;
      const sameBox = Math.floor(Math.floor(first / size) / Math.sqrt(size)) ===
        Math.floor(Math.floor(second / size) / Math.sqrt(size)) &&
        Math.floor((first % size) / Math.sqrt(size)) ===
        Math.floor((second % size) / Math.sqrt(size));
      if (duplicate.filled[second] === value && (sameRow || sameColumn || sameBox)) {
        controllerClashes.add(first);
        controllerClashes.add(second);
      }
    }
  }
  assert.deepEqual([...controllerClashes].sort((a, b) => a - b), oracle.wrong_clashes,
    "the controller's duplicate cells must match the original UI clash set");

  const wrongFull = oracle.trace[oracle.wrong_full_trace_index];
  assert.deepEqual(wrongFull.state, oracle.wrong_full_state,
    "the original wrong full-grid checkpoint must be captured at the expected action");
  assert.equal(wrongFull.state[0], 1,
    "a wrong full grid must remain in SOLVING until corrected");
  assert.equal(wrongFull.state[9], 0,
    "the wrong-grid checkpoint must contain no empty cells");
  assert.equal(wrongFull.state[8], -1,
    "the source does not show a verdict for an incorrect full grid");

  assert.deepEqual(state(), oracle.solved_state,
    "the completed source solution/slip verdict diverged");
  assert.equal(info(17), oracle.score.solved, "solved count diverged");
  assert.equal(info(18), oracle.score.slips, "slip count diverged");
  assert.equal(info(19), oracle.score.best_rung, "best rung diverged");
  assert.equal(action(ACTION.start), STATUS_ACCEPTED,
    "Space should advance the solved puzzle to the run summary");
  assert.deepEqual(state(), oracle.done_state,
    "the final source run summary diverged");
  console.log(`sudoku_original_replay_test: PASS (${oracle.trace.length} exact SudokuEnv source-port actions, generation, clue protection, pencil masks, clashes, wrong full grid, verdict, score, and DONE)`);
} finally {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
}
