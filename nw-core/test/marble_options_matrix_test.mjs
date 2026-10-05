// Marble Maze options and controller-lifecycle matrix.
//
// The native task resets the same MarbleMaze object when its options are
// applied.  That reset must clear the visible run while preserving the
// persistent CPython-compatible RNG stream.  This test exercises the exact
// controller ABI used by the browser for every source-supported level,
// trial-count choice, adaptive choice, and time override.  It deliberately
// does not construct MuJoCo models: physics ownership is covered by the
// generated-session tests, while this matrix isolates the state boundary
// that used to be easy to get wrong during a live options edit.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const wasmPath = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasmPath), {
  warn: false,
});

const TASK_MARBLE = 642986n;
const STATUS = Object.freeze({ accepted: 1n });
const EVENT_ACTION = 1n;
const ACTION = Object.freeze({
  start: 0n,
  report: 3n,
  boardReady: 4n,
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
  boardGeneration: 4,
  seed: 5,
  elapsed: 6,
  remaining: 7,
  verdict: 8,
  wins: 9,
  losses: 10,
  heldMask: 11,
  resultCount: 12,
});
const STATE_BYTES = 112n;
const STATE_POINTER = Number(exports.nw_frame_alloc(STATE_BYTES));
assert.ok(STATE_POINTER > 0, "WASM state buffer allocation failed");

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
function resetClock() {
  sequence = 0n;
  timestamp = 0n;
}

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

function create(seed = 0x12345678) {
  return exports.nw_api_v1_create(
    TASK_MARBLE, 1n, 1n, 1n, 0n, 2600n, 0n, 1n, BigInt(seed));
}

function applyOptions(handle, rung, trials, adaptive, seconds) {
  return exports.nw_api_v1_marble_apply_options(
    handle, BigInt(rung), BigInt(trials), BigInt(adaptive), BigInt(seconds));
}

function marbleInfo(handle, field) {
  return exports.nw_api_v1_marble_info(handle, BigInt(field));
}

function startAndReadIdentity(handle) {
  assert.equal(dispatch(handle, ACTION.start), STATUS.accepted);
  const state = readState(handle);
  assert.equal(state[INFO.phase], PHASE.running);
  const grain = exports.nw_api_v1_marble_grain_seed(handle);
  assert.ok(Number.isFinite(grain) && grain >= 0 && grain < 4,
    "Marble grain seed is outside the source renderer range");
  return { state, grain };
}

// Every combination exposed by the source TaskOptions screen must be
// accepted, reset to READY, and expose the selected values before Space is
// pressed again.  The zero override means "by level"; the other values are
// the complete source menu, not arbitrary controller values.
const trialOptions = [1, 2, 3, 5, 8, 10];
const timeOptions = [0, 15_000, 30_000, 45_000, 60_000, 90_000, 120_000];
let matrixCases = 0;
for (let rung = 1; rung <= 16; rung += 1) {
  for (const trials of trialOptions) {
    for (const adaptive of [0, 1]) {
      for (const seconds of timeOptions) {
        matrixCases += 1;
        resetClock();
        const handle = create(0x51000000 + matrixCases);
        assert.ok(handle > 0n, `controller allocation failed for case ${matrixCases}`);
        try {
          const initial = readState(handle);
          assert.equal(initial[INFO.phase], PHASE.ready);
          assert.equal(initial[INFO.trial], 0n);
          assert.equal(initial[INFO.seed], 0n,
            "READY must not consume a board identity");

          assert.equal(applyOptions(handle, rung, trials, adaptive, seconds),
            STATUS.accepted,
            `options rejected for rung ${rung}, trials ${trials}, ` +
            `adaptive ${adaptive}, seconds ${seconds}`);
          const reset = readState(handle);
          assert.equal(reset[INFO.phase], PHASE.ready);
          assert.equal(reset[INFO.rung], BigInt(rung));
          assert.equal(reset[INFO.totalTrials], BigInt(trials));
          assert.equal(reset[INFO.trial], 0n);
          assert.equal(reset[INFO.elapsed], 0n);
          assert.equal(reset[INFO.verdict], -1n);
          assert.equal(reset[INFO.wins], 0n);
          assert.equal(reset[INFO.losses], 0n);
          assert.equal(reset[INFO.heldMask], 0n);
          assert.equal(marbleInfo(handle, INFO.resultCount), 0n);
          assert.equal(reset[INFO.remaining] > 0n, true);

          const running = startAndReadIdentity(handle);
          assert.equal(running.state[INFO.rung], BigInt(rung));
          assert.equal(running.state[INFO.totalTrials], BigInt(trials));
          assert.equal(running.state[INFO.remaining],
            seconds === 0 ? running.state[INFO.remaining] : BigInt(seconds),
            "a fixed time override must become the active tray budget");

          // Applying options while a tray is live is the browser's C/options
          // path. It must invalidate the old tray and not leave a held input,
          // verdict, result row, or active clock behind.
          const liveRung = rung === 16 ? 1 : rung + 1;
          const liveTrials = trials === 10 ? 1 : trials + 1;
          const liveSeconds = timeOptions[
            (timeOptions.indexOf(seconds) + 1) % timeOptions.length
          ];
          assert.equal(applyOptions(handle, liveRung, liveTrials, 1 - adaptive,
            liveSeconds), STATUS.accepted);
          const liveReset = readState(handle);
          assert.equal(liveReset[INFO.phase], PHASE.ready);
          assert.equal(liveReset[INFO.rung], BigInt(liveRung));
          assert.equal(liveReset[INFO.totalTrials], BigInt(liveTrials));
          assert.equal(liveReset[INFO.trial], 0n);
          assert.equal(liveReset[INFO.elapsed], 0n);
          assert.equal(liveReset[INFO.heldMask], 0n);
          assert.equal(marbleInfo(handle, INFO.resultCount), 0n);
        } finally {
          assert.equal(exports.nw_api_v1_destroy(handle), 0n,
            `controller destroy failed for case ${matrixCases}`);
        }
      }
    }
  }
}

// Invalid values must be rejected before mutating the live controller. This
// protects the browser options screen from leaving a half-applied run when a
// stale localStorage value or a hostile debug URL reaches the ABI.
const invalidOptions = [
  [0, 1, 0, 0], [17, 1, 0, 0],
  [1, 0, 0, 0], [1, 1001, 0, 0],
  [1, 1, 0, 1], [1, 1, 0, 15_001],
  [1, 1, 0, 600_001],
];
for (const [rung, trials, adaptive, seconds] of invalidOptions) {
  resetClock();
  const handle = create(0x72000000 + rung + trials + seconds);
  assert.ok(handle > 0n);
  try {
    const before = readState(handle);
    assert.ok(applyOptions(handle, rung, trials, adaptive, seconds) < 0n,
      `invalid options were accepted: ${rung}/${trials}/${adaptive}/${seconds}`);
    assert.deepEqual(readState(handle), before,
      "rejected options mutated the controller");
  } finally {
    assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  }
}

// Applying options is a reset, not a reseed. Compare its second board identity
// with a fresh controller that consumes the first board and then starts a new
// run. Both the board seed and the renderer grain draw belong to the same
// persistent source RNG stream.
resetClock();
const applied = create(987654321);
assert.ok(applied > 0n);
const fresh = create(987654321);
assert.ok(fresh > 0n);
try {
  const firstApplied = startAndReadIdentity(applied);
  const firstFresh = startAndReadIdentity(fresh);
  assert.equal(firstApplied.state[INFO.seed], firstFresh.state[INFO.seed]);
  assert.equal(firstApplied.grain, firstFresh.grain);

  assert.equal(applyOptions(applied, 7, 3, 1, 30_000), STATUS.accepted);
  const secondApplied = startAndReadIdentity(applied);

  // Finish the fresh controller's one-tray run through the same result and
  // feedback barrier the browser uses, then start its next run. This consumes
  // exactly one board identity pair without involving host physics.
  assert.equal(dispatch(fresh, ACTION.report, 0n, 1_000n), STATUS.accepted);
  assert.equal(dispatch(fresh, ACTION.recordResult, 0n, 0n), STATUS.accepted);
  assert.equal(advance(fresh, 2_600), STATUS.accepted);
  assert.equal(readState(fresh)[INFO.phase], PHASE.done);
  assert.equal(dispatch(fresh, ACTION.start), STATUS.accepted);
  assert.equal(readState(fresh)[INFO.phase], PHASE.preparing);
  assert.equal(dispatch(fresh, ACTION.boardReady), STATUS.accepted);
  const secondFresh = readState(fresh);
  const secondFreshGrain = exports.nw_api_v1_marble_grain_seed(fresh);

  assert.equal(secondApplied.state[INFO.seed], secondFresh[INFO.seed],
    "options reset reseeded the board stream");
  assert.equal(secondApplied.grain, secondFreshGrain,
    "options reset changed the renderer grain stream");
} finally {
  assert.equal(exports.nw_api_v1_destroy(applied), 0n);
  assert.equal(exports.nw_api_v1_destroy(fresh), 0n);
}

console.log(`PASS: Marble options/controller matrix (${matrixCases} valid ` +
  "combinations, invalid-input rejection, and persistent RNG reset)");
