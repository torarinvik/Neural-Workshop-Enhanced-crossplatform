// Generated-board Marble multi-trial lifecycle matrix.
//
// This is a host-level replay of the same boundaries used by the browser:
// Space starts a board, the official MuJoCo adapter owns the physical tray,
// the common controller owns the active/feedback clocks, and the host commits
// the physics result before the feedback barrier can deal the next tray.
// Unlike marble_generated_session_test.mjs, this matrix deliberately crosses
// the feedback -> PREPARING -> BOARD_READY boundary more than once and checks
// both adaptive and fixed-rung runs.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decodeMarbleBoard } from "../shells/web/marble-maze.js";
import { loadMarbleMazeMuJoCo } from "../shells/web/marble-maze-mujoco.js";

const wasmPath = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasmPath), {
  warn: false,
});
const candidateModule = process.env.NW_MUJOCO_WASM_MODULE;
const candidateLoader = candidateModule ?
  (await import(pathToFileURL(path.resolve(candidateModule)).href)).default : undefined;
const Game = await loadMarbleMazeMuJoCo(candidateLoader);

const TASK_MARBLE = 642986n;
const STATUS = Object.freeze({ accepted: 1n });
const EVENT_ACTION = 1n;
const ACTION = Object.freeze({
  start: 0n,
  boardReady: 4n,
  score: 10n,
  syncSettleTime: 11n,
  recordResult: 12n,
});
const PHASE = Object.freeze({
  ready: 0n,
  running: 1n,
  feedback: 2n,
  preparing: 3n,
  done: 4n,
});
const INFO = Object.freeze({
  phase: 0,
  rung: 1,
  trial: 2,
  totalTrials: 3,
  seed: 5,
  elapsed: 6,
  feedbackRemaining: 7,
  verdict: 8,
});
const RESULT = Object.freeze({
  rung: 100n,
  elapsed: 101n,
  home: 102n,
  lost: 103n,
  verdict: 104n,
  scoreWin: 105n,
  boardSeed: 106n,
});
const STATE_BYTES = 112n;
const STATE_POINTER = Number(exports.nw_frame_alloc(STATE_BYTES));
const BOARD_CAPACITY = 65536n;
const BOARD_POINTER = Number(exports.nw_frame_alloc(BOARD_CAPACITY));
assert.ok(STATE_POINTER > 0 && BOARD_POINTER > 0,
  "WASM test buffers could not be allocated");

function readState(handle) {
  const length = exports.nw_api_v1_read_state(
    handle, BigInt(STATE_POINTER), STATE_BYTES);
  assert.equal(length, STATE_BYTES);
  const view = new DataView(
    instance.exports.memory.buffer, STATE_POINTER, Number(length));
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function boardForState(state) {
  const length = Number(exports.nw_marble_board_write(
    BigInt(BOARD_POINTER), BOARD_CAPACITY,
    state[INFO.rung], state[INFO.seed]));
  assert.ok(length > 0, "WASM did not produce the controller's board");
  return decodeMarbleBoard(new Uint8Array(
    instance.exports.memory.buffer, BOARD_POINTER, length));
}

function resultValue(handle, field, index = 0n) {
  return exports.nw_api_v1_marble_value(handle, field, index);
}

let timestamp = 0n;
let sequence = 0n;
function dispatch(handle, action, value = 0n, aux = 0n) {
  timestamp += 1n;
  sequence += 1n;
  return exports.nw_api_v1_dispatch(
    handle, EVENT_ACTION, timestamp, sequence, action, value, 0n,
    0n, 0n, 0n, aux);
}

function advance(handle, elapsedMs) {
  timestamp += BigInt(elapsedMs);
  sequence += 1n;
  return exports.nw_api_v1_advance(
    handle, timestamp, BigInt(elapsedMs), sequence);
}

// No-tilt timeouts are intentional here. They keep the physical path real
// while making the expected adaptive decision unambiguous: the physics has
// not reached the home cup, so every adaptive timeout lowers the next rung.
// The separate generated-play test covers held-input solved/lost outcomes.
const cases = [
  { rung: 1, trials: 2, adaptive: false, seconds: 15000, runSeed: 17 },
  { rung: 4, trials: 3, adaptive: true, seconds: 15000, runSeed: 314159 },
  { rung: 16, trials: 2, adaptive: true, seconds: 30000, runSeed: 1 },
];
const resourceStats = globalThis.__NW_MARBLE_MUJOCO_RESOURCE_STATS__;
assert.equal(typeof resourceStats, "function");
const resourceBaseline = resourceStats();

let completedTrials = 0;
for (const testCase of cases) {
  timestamp = 0n;
  sequence = 0n;
  const handle = exports.nw_api_v1_create(
    TASK_MARBLE, 1n, BigInt(testCase.rung), BigInt(testCase.trials),
    BigInt(testCase.adaptive ? 1 : 0), 2600n, BigInt(testCase.seconds),
    1n, BigInt(testCase.runSeed));
  assert.ok(handle > 0n, `controller allocation failed for ${testCase.rung}`);
  let game = null;
  let destroyed = false;
  const rows = [];
  try {
    let state = readState(handle);
    assert.equal(state[INFO.phase], PHASE.ready);
    assert.equal(state[INFO.trial], 0n);
    assert.equal(exports.nw_api_v1_marble_info(handle, 12n), 0n);
    assert.equal(state[INFO.totalTrials], BigInt(testCase.trials));
    assert.equal(dispatch(handle, ACTION.start), STATUS.accepted);

    for (let trialIndex = 0; trialIndex < testCase.trials; trialIndex++) {
      state = readState(handle);
      assert.equal(state[INFO.phase], PHASE.running,
        `trial ${trialIndex + 1} did not enter RUNNING`);
      assert.equal(state[INFO.trial], BigInt(trialIndex + 1));
      const trialRung = Number(state[INFO.rung]);
      const board = boardForState(state);
      game = new Game(board);

      // Advance in the source UI's exact 50 ms clamp. Generated starts are
      // away from holes, so no tilt gives a stable physical timeout while
      // still constructing and stepping every native model/data pair.
      const frameCount = testCase.seconds / 50;
      for (let frame = 0; frame < frameCount; frame++) {
        game.advance(0.05, new Set());
        assert.equal(game.settled, false,
          `tray settled before timeout (case ${testCase.runSeed}, ` +
          `trial ${trialIndex + 1}, frame ${frame})`);
        assert.equal(advance(handle, 50), STATUS.accepted);
        state = readState(handle);
        if (state[INFO.phase] === PHASE.feedback) break;
      }

      state = readState(handle);
      assert.equal(state[INFO.phase], PHASE.feedback,
        `timeout did not enter feedback (case ${testCase.runSeed}, ` +
        `trial ${trialIndex + 1})`);
      assert.equal(state[INFO.elapsed], BigInt(testCase.seconds));
      assert.equal(state[INFO.verdict], 0n);
      assert.equal(dispatch(handle, ACTION.syncSettleTime,
        BigInt(Math.round(game.elapsed * 1000))), STATUS.accepted);
      // This deliberately retains the source score() quirk: a timeout with
      // zero lost marbles is physically a loss but scores as a win.
      const scoreWin = game.lost === 0 ? 1n : 0n;
      assert.equal(dispatch(handle, ACTION.score, scoreWin), STATUS.accepted);
      assert.equal(dispatch(handle, ACTION.recordResult,
        BigInt(game.home), BigInt(game.lost)), STATUS.accepted);

      const row = {
        rung: BigInt(trialRung),
        elapsed: BigInt(Math.round(game.elapsed * 1000)),
        home: BigInt(game.home),
        lost: BigInt(game.lost),
        verdict: 0n,
        scoreWin,
        boardSeed: state[INFO.seed],
      };
      rows.push(row);
      completedTrials += 1;
      state = readState(handle);
      assert.equal(exports.nw_api_v1_marble_info(handle, 12n), BigInt(trialIndex + 1));
      for (const [field, expected] of Object.entries({
        rung: row.rung, elapsed: row.elapsed, home: row.home,
        lost: row.lost, verdict: row.verdict, scoreWin: row.scoreWin,
        boardSeed: row.boardSeed,
      })) {
        assert.equal(resultValue(handle, RESULT[field], BigInt(trialIndex)), expected,
          `result row field ${field} differs on trial ${trialIndex + 1}`);
      }

      game.disposeEngine();
      game = null;
      // Qualify the boundary, not only a jump which happens to reach DONE.
      // Original UI transitions at now >= until (2.6 seconds of wall time).
      const feedbackState = readState(handle);
      assert.equal(advance(handle, 2599), STATUS.accepted);
      state = readState(handle);
      assert.equal(state[INFO.phase], PHASE.feedback,
        "feedback must not advance a tray one millisecond early");
      assert.equal(state[INFO.feedbackRemaining], 1n);
      assert.equal(state[INFO.seed], feedbackState[INFO.seed]);
      assert.equal(exports.nw_api_v1_marble_info(handle, 12n), BigInt(trialIndex + 1),
        "feedback waiting must not duplicate the result row");
      advance(handle, 0);
      assert.deepEqual(readState(handle), state,
        "zero-time feedback update must preserve the complete state");
      assert.equal(advance(handle, 1), STATUS.accepted);
      state = readState(handle);
      if (trialIndex + 1 < testCase.trials) {
        assert.equal(state[INFO.phase], PHASE.preparing);
        const nextBoard = boardForState(state);
        game = new Game(nextBoard);
        assert.equal(dispatch(handle, ACTION.boardReady), STATUS.accepted);
      } else {
        assert.equal(state[INFO.phase], PHASE.done);
      }
    }

    assert.equal(rows.length, testCase.trials);
    assert.equal(readState(handle)[INFO.phase], PHASE.done);
    const expectedRungs = rows.map((row, index) => testCase.adaptive
      ? BigInt(Math.max(1, testCase.rung - index))
      : BigInt(testCase.rung));
    assert.deepEqual(rows.map((row) => row.rung), expectedRungs,
      `adaptive rung history differs for run seed ${testCase.runSeed}`);
    assert.equal(exports.nw_api_v1_destroy(handle), 0n);
    destroyed = true;
  } finally {
    if (game) game.disposeEngine();
    if (!destroyed) exports.nw_api_v1_destroy(handle);
    const resources = resourceStats();
    assert.equal(resources.liveModels, resourceBaseline.liveModels,
      `MuJoCo model leak in multi-trial case ${testCase.runSeed}`);
    assert.equal(resources.liveData, resourceBaseline.liveData,
      `MuJoCo data leak in multi-trial case ${testCase.runSeed}`);
  }
}

console.log(`PASS: Marble multi-trial/adaptive sessions (${cases.length} ` +
  `cases; ${completedTrials} real timeout trays, result history, ` +
  "next-board handoff, and cleanup)");
