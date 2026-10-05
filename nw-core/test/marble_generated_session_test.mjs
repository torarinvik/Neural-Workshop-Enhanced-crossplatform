// Generated-board Marble session matrix.
//
// This is deliberately a test-only host replay. It drives the same common
// controller actions that the browser shell uses, while the official MuJoCo
// adapter owns the physical tray. The matrix is intentionally a timeout
// exercise: it proves that every generated rung can survive the complete
// board -> physics -> timeout -> score -> result-history -> DONE lifecycle,
// without pretending that a fixed input trace solves arbitrary generated
// boards.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decodeMarbleBoard } from "../shells/web/marble-maze.js";
import { loadMarbleMazeMuJoCo } from "../shells/web/marble-maze-mujoco.js";

const wasmPath = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasmPath), {
  warn: false,
});
const Game = await loadMarbleMazeMuJoCo();
const resourceStats = globalThis.__NW_MARBLE_MUJOCO_RESOURCE_STATS__;
assert.equal(typeof resourceStats, "function",
  "MuJoCo resource diagnostics are not available");
const resourceBaseline = resourceStats();

const TASK_MARBLE = 642986n;
const STATUS = Object.freeze({ accepted: 1n });
const EVENT_ACTION = 1n;
const ACTION = Object.freeze({
  start: 0n,
  score: 10n,
  syncSettleTime: 11n,
  recordResult: 12n,
});
const PHASE = Object.freeze({
  running: 1n,
  feedback: 2n,
  done: 4n,
});
const INFO = Object.freeze({
  phase: 0,
  rung: 1,
  trial: 2,
  trials: 3,
  seed: 5,
  elapsed: 6,
  verdict: 8,
});
const INFO_RESULT_COUNT = 12n;
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
assert.ok(STATE_POINTER > 0, "WASM state buffer allocation failed");

function create(options, seed) {
  return exports.nw_api_v1_create(TASK_MARBLE, 1n, ...options, BigInt(seed));
}

function readState(handle) {
  const length = exports.nw_api_v1_read_state(
    handle, BigInt(STATE_POINTER), STATE_BYTES);
  assert.equal(length, STATE_BYTES, "Marble state ABI length changed");
  const view = new DataView(
    instance.exports.memory.buffer, STATE_POINTER, Number(length));
  assert.equal(view.getUint32(0, true), 0x3152574e,
    "Marble state envelope magic changed");
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

let sequence = 0n;
let timestamp = 0n;
function dispatch(handle, action, value = 0n, aux = 0n) {
  sequence += 1n;
  timestamp += 1n;
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

function resultValue(handle, field, index = 0n) {
  return exports.nw_api_v1_marble_value(handle, field, index);
}

function resultCount(handle) {
  return exports.nw_api_v1_marble_info(handle, INFO_RESULT_COUNT);
}

function makeBoard(rung, seed) {
  const capacity = 65536n;
  const pointer = Number(exports.nw_frame_alloc(capacity));
  assert.ok(pointer > 0, "WASM board buffer allocation failed");
  const length = Number(exports.nw_marble_board_write(
    BigInt(pointer), capacity, BigInt(rung), BigInt(seed)));
  assert.ok(length > 0, `WASM board generation failed for rung ${rung}`);
  return decodeMarbleBoard(new Uint8Array(
    instance.exports.memory.buffer, pointer, length));
}

// These are the same five deterministic run seeds used by the certified
// board transport and headed browser matrix. Repeating them at every rung
// exercises the controller's actual persistent MT19937 stream while the rung
// changes the generated tray geometry and physical object count.
const runSeeds = [0, 1, 17, 314159, 1073741823];
let cases = 0;
let maximumWalls = 0;
let maximumHoles = 0;
let maximumMarbles = 0;

for (let rung = 1; rung <= 16; rung++) {
  for (const runSeed of runSeeds) {
    cases += 1;
    sequence = 0n;
    timestamp = 0n;
    // Use the source-supported 15-second option so the full matrix remains a
    // bounded CI test. Adaptive progression is off: the result must retain
    // the rung that actually generated the tray.
    const handle = create([BigInt(rung), 1n, 0n, 2600n, 15000n, 1n], runSeed);
    assert.ok(handle > 0n, `controller allocation failed for rung ${rung}`);
    let game = null;
    try {
      const ready = readState(handle);
      assert.equal(ready[INFO.phase], 0n);
      assert.equal(ready[INFO.trial], 0n);
      assert.equal(ready[INFO.seed], 0n,
        "READY must not consume a generated board identity");

      assert.equal(dispatch(handle, ACTION.start), STATUS.accepted,
        `Space/start rejected for rung ${rung}, seed ${runSeed}`);
      let state = readState(handle);
      assert.equal(state[INFO.phase], PHASE.running);
      assert.equal(state[INFO.trial], 1n);
      const boardSeed = state[INFO.seed];
      assert.ok(boardSeed >= 0n && boardSeed < 1073741824n);

      const board = makeBoard(rung, boardSeed);
      maximumWalls = Math.max(maximumWalls, board.walls.length);
      maximumHoles = Math.max(maximumHoles, board.holes.length);
      maximumMarbles = Math.max(maximumMarbles, board.starts.length);
      game = new Game(board);

      // With no tilt, generated trays remain active at their starts. Advance
      // in the exact source UI frame clamp (300 x 50 ms) so this is also a
      // physical timeout test, not merely a controller-clock shortcut.
      for (let frame = 0; frame < 300; frame++) {
        game.advance(0.05, new Set());
        assert.equal(game.settled, false,
          `generated tray settled unexpectedly before timeout ` +
          `(rung ${rung}, run seed ${runSeed}, frame ${frame})`);
        assert.equal(advance(handle, 50), STATUS.accepted);
        state = readState(handle);
        if (state[INFO.phase] === PHASE.feedback) break;
      }

      state = readState(handle);
      assert.equal(state[INFO.phase], PHASE.feedback,
        `timeout did not enter feedback for rung ${rung}, seed ${runSeed}`);
      assert.equal(state[INFO.elapsed], 15000n);
      assert.equal(state[INFO.verdict], 0n);

      const syncedMs = BigInt(Math.round(game.elapsed * 1000));
      assert.equal(syncedMs, 15000n,
        `physics/controller timeout clocks diverged for rung ${rung}, seed ${runSeed}`);
      assert.equal(dispatch(handle, ACTION.syncSettleTime, syncedMs), STATUS.accepted);
      // The native score() counts a row with zero lost marbles as a win even
      // when the timeout verdict is a loss. Preserve that observable quirk.
      assert.equal(dispatch(handle, ACTION.score, game.lost === 0 ? 1n : 0n),
        STATUS.accepted);
      assert.equal(dispatch(handle, ACTION.recordResult, BigInt(game.home),
        BigInt(game.lost)), STATUS.accepted);

      state = readState(handle);
      assert.equal(resultCount(handle), 1n);
      assert.equal(state[INFO.verdict], 0n);
      assert.equal(resultValue(handle, RESULT.rung), BigInt(rung));
      assert.equal(resultValue(handle, RESULT.elapsed), 15000n);
      assert.equal(resultValue(handle, RESULT.home), BigInt(game.home));
      assert.equal(resultValue(handle, RESULT.lost), BigInt(game.lost));
      assert.equal(resultValue(handle, RESULT.verdict), 0n);
      assert.equal(resultValue(handle, RESULT.scoreWin), game.lost === 0 ? 1n : 0n);
      assert.equal(resultValue(handle, RESULT.boardSeed), boardSeed);

      assert.equal(advance(handle, 2600), STATUS.accepted);
      state = readState(handle);
      assert.equal(state[INFO.phase], PHASE.done,
        `one-tray timeout did not finish for rung ${rung}, seed ${runSeed}`);
      assert.equal(exports.nw_api_v1_destroy(handle), 0n);
    } finally {
      if (game) game.disposeEngine();
      const resources = resourceStats();
      assert.equal(resources.liveModels, resourceBaseline.liveModels,
        `MuJoCo model leak after rung ${rung}, run seed ${runSeed}`);
      assert.equal(resources.liveData, resourceBaseline.liveData,
        `MuJoCo data leak after rung ${rung}, run seed ${runSeed}`);
    }
  }
}

console.log(`PASS: generated Marble session matrix (${cases} cases; ` +
  `max ${maximumWalls} walls, ${maximumHoles} holes, ` +
  `${maximumMarbles} marbles; official MuJoCo timeout/result lifecycle)`);
