// Common-v1 lifecycle smoke for the source-backed Sudoku controller.
//
// The solution is deliberately read only through the diagnostic value
// accessor used by focused tests. The browser route never receives it: its
// only production inputs are cursor movement, pencil mode, erase, and the
// digit value typed by the player.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_sudoku());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n });
const ACTION = Object.freeze({
  start: 0n, up: 1n, down: 2n, left: 3n, right: 4n,
  write: 5n, erase: 6n, pencil: 7n,
});
const PHASE = Object.freeze({ ready: 0n, solving: 1n, solved: 2n, done: 3n });
const INFO = Object.freeze({
  phase: 0, rung: 1, trial: 2, totalTrials: 3, size: 4, cursor: 5,
  pencil: 6, mistakes: 7, verdict: 8, blanks: 9, showClashes: 10,
  hasPuzzle: 11,
});
const VALUE = Object.freeze({ given: 0n, solution: 1n, filled: 2n, marks: 3n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [3n, 1n, 1n, 1n, 0n, 0n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function dispatch(handle, kind, timestamp, sequence, code, value = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, 0n, 0n, 0n);
}

let timestamp = 100;
let sequence = 0;
function action(handle, code, value = 0n) {
  return dispatch(handle, EVENT.action, timestamp++, sequence++, code, value);
}

function state(handle) {
  const length = exports.nw_api_v1_read_state(handle,
    BigInt(STATE_BUFFER), BigInt(STATE_BYTES));
  assert.equal(length, BigInt(STATE_BYTES));
  const view = new DataView(instance.exports.memory.buffer,
    STATE_BUFFER, STATE_BYTES);
  assert.equal(view.getUint32(0, true), 0x3152574e);
  assert.equal(view.getUint32(4, true), 1);
  assert.equal(view.getUint32(12, true), 12);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_sudoku_info(handle, BigInt(field)));
}

function value(handle, field, at) {
  return BigInt(exports.nw_api_v1_sudoku_value(handle, field, BigInt(at)));
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function textLines(bytes) {
  return decode(bytes).filter(({ kind }) => kind === Kind.TEXT)
    .map(({ text }) => text);
}

function hasText(bytes, expected) {
  return textLines(bytes).some((line) => line.includes(expected));
}

function moveTo(handle, size, target) {
  const current = Number(state(handle)[INFO.cursor]);
  let row = Math.floor(current / size);
  let column = current % size;
  const targetRow = Math.floor(target / size);
  const targetColumn = target % size;
  while (row > targetRow) {
    assert.equal(action(handle, ACTION.up), STATUS.accepted);
    row -= 1;
  }
  while (row < targetRow) {
    assert.equal(action(handle, ACTION.down), STATUS.accepted);
    row += 1;
  }
  while (column > targetColumn) {
    assert.equal(action(handle, ACTION.left), STATUS.accepted);
    column -= 1;
  }
  while (column < targetColumn) {
    assert.equal(action(handle, ACTION.right), STATUS.accepted);
    column += 1;
  }
  assert.equal(state(handle)[INFO.cursor], BigInt(target));
}

assert.equal(TASK, 4211466488n, "Sudoku keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
for (const options of [
  [0n, 1n, 1n, 1n, 0n, 0n],
  [3n, 4n, 1n, 1n, 0n, 0n],
  [3n, 1n, 2n, 1n, 0n, 0n],
  [3n, 1n, 1n, 2n, 0n, 0n],
  [3n, 1n, 1n, 1n, 1n, 0n],
]) {
  assert.equal(create(options), STATUS.badOptions,
    `bad options accepted: ${options}`);
}

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 3n, 0n, 1n, 0n, 0n, 0n, 0n, -1n, 0n, 1n, 0n]);
assert.equal(info(run, 11), 1n, "source show-clashes option is retained");
assert.equal(info(run, 12), 1n, "source adaptive option is retained");
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(hasText(readyFrame, "Sudoku"));
assert.ok(hasText(readyFrame, "Press Space to start"));

// The typed action and key-event paths must deal the same seeded puzzle.
assert.equal(action(run, ACTION.start), STATUS.accepted);
assert.equal(dispatch(replay, EVENT.keyDown, timestamp++, sequence++, 1n),
  STATUS.accepted);
assert.deepEqual(state(run), state(replay), "start action and Space diverged");
const started = state(run);
assert.equal(started[INFO.phase], PHASE.solving);
assert.equal(started[INFO.trial], 1n);
assert.equal(started[INFO.size], 9n);
assert.equal(started[INFO.hasPuzzle], 1n);
assert.ok(started[INFO.blanks] > 0n && started[INFO.blanks] < 81n);
assert.equal(info(run, 6), 81n, "9x9 puzzle has 81 cells");
assert.ok(info(run, 15) >= 0n, "generator tier is retained");
assert.ok(hasText(frame(run), "puzzle 1/1"));

const size = Number(started[INFO.size]);
const cells = size * size;
const givens = Array.from({ length: cells }, (_, at) => value(run, VALUE.given, at));
const solution = Array.from({ length: cells }, (_, at) => value(run, VALUE.solution, at));
assert.ok(givens.some((held) => held !== 0n));
assert.ok(givens.some((held) => held === 0n));
assert.deepEqual(givens, Array.from({ length: cells }, (_, at) => value(replay, VALUE.given, at)));
assert.deepEqual(solution, Array.from({ length: cells }, (_, at) => value(replay, VALUE.solution, at)));

const given = givens.findIndex((held) => held !== 0n);
const blank = givens.findIndex((held) => held === 0n);
moveTo(run, size, given);
const givenBefore = state(run);
assert.equal(action(run, ACTION.write, givens[given]), STATUS.accepted);
assert.equal(value(run, VALUE.filled, given), givens[given],
  "a given cannot be overwritten");
assert.equal(state(run)[INFO.mistakes], givenBefore[INFO.mistakes]);

moveTo(run, size, blank);
const answer = solution[blank];
assert.equal(action(run, ACTION.pencil), STATUS.accepted);
assert.equal(state(run)[INFO.pencil], 1n);
assert.equal(action(run, ACTION.write, answer), STATUS.accepted);
assert.equal(value(run, VALUE.filled, blank), 0n,
  "pencil mode must not fill the cell");
assert.equal(value(run, VALUE.marks, blank), 1n << (answer - 1n));
assert.equal(action(run, ACTION.erase), STATUS.accepted);
assert.equal(value(run, VALUE.marks, blank), 0n);
assert.equal(action(run, ACTION.pencil), STATUS.accepted);
assert.equal(state(run)[INFO.pencil], 0n);

const wrong = answer === BigInt(size) ? 1n : answer + 1n;
assert.notEqual(wrong, answer);
assert.equal(action(run, ACTION.write, wrong), STATUS.accepted);
assert.equal(value(run, VALUE.filled, blank), wrong);
assert.equal(state(run)[INFO.mistakes], 1n);
assert.equal(action(run, ACTION.erase), STATUS.accepted);

// Solve every non-given cell through the same cursor/actions a browser player
// uses. The controller, not the test, decides when the full grid is correct.
for (let at = 0; at < cells; at += 1) {
  if (givens[at] !== 0n) continue;
  moveTo(run, size, at);
  assert.equal(action(run, ACTION.write, solution[at]), STATUS.accepted);
}
// The wrong attempt remains part of the slip count, but the final cell should
// trigger a solved verdict once all non-givens contain their source answers.
const finalBlank = state(run)[INFO.blanks];
assert.equal(finalBlank, 0n);
assert.equal(state(run)[INFO.phase], PHASE.solved);
assert.equal(state(run)[INFO.verdict], 0n);
assert.equal(info(run, 17), 1n);
assert.equal(info(run, 18), 1n);
const solvedFrame = frame(run);
assert.ok(hasText(solvedFrame, "Solved in"));
assert.ok(hasText(solvedFrame, "1 slips"));

// With one configured trial, Space advances the solved screen to the stable
// DONE summary while preserving the run verdict and score.
assert.equal(action(run, ACTION.start), STATUS.accepted);
assert.equal(state(run)[INFO.phase], PHASE.done);
assert.equal(state(run)[INFO.verdict], 0n);
assert.ok(hasText(frame(run), "1 solved, 1 slips"));

for (const handle of [run, replay]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Sudoku source-backed generation, seeded replay, givens, pencil marks, cursor input, real grading, verdict, completion, render, and cleanup");
