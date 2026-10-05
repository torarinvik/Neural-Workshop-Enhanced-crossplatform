// Common-v1 lifecycle, timing, visibility, grading, and 3D-pattern checks for
// the only N-Back route in the port. Generic 2D/dual/audio N-Back is not part
// of this test or of the browser task registry.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
for (const name of ["nw_crab_back", "nw_frame_write", "nw_session_frame_write",
                    "nw_batch_write", "nw_menu_write", "nw_menu_state_write"]) {
  assert.equal(typeof exports[name], "undefined",
    "legacy non-3D N-Back export leaked into the browser artifact: " + name);
}
for (const name of ["nw_api_v1_task_nback_3d", "nw_api_v1_nback3d_info",
                    "nw_api_v1_create", "nw_api_v1_render"]) {
  assert.equal(typeof exports[name], "function",
    "required 3D N-Back export is missing: " + name);
}

const TASK = BigInt(exports.nw_api_v1_task_nback_3d());
const EVENT_ACTION = 1n;
const ACTION = Object.freeze({ start: 0n, match: 1n, tick: 2n, pause: 3n, restart: 4n });
const FIELD = Object.freeze({
  phase: 0, nback: 1, trial: 2, total: 3, cubes: 4, position: 5,
  color: 6, verdict: 7, answered: 8, hits: 9, misses: 10,
  falseAlarms: 11,
});
const INFO = Object.freeze({ deadline: 13, interval: 14, stimulus: 15,
  feedback: 16, seed: 17, paused: 18, error: 19 });
const PHASE = Object.freeze({ ready: 0n, stimulus: 1n, response: 2n,
  feedback: 3n, done: 4n, paused: 5n, error: 6n, startup: 7n });
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const FRAME_CAPACITY = 65536n;
const statePtr = Number(exports.nw_frame_alloc(112n));
const framePtr = Number(exports.nw_frame_alloc(FRAME_CAPACITY));
const snapshotPtr = Number(exports.nw_frame_alloc(FRAME_CAPACITY));
assert.ok(TASK > 0n && statePtr > 0 && framePtr > 0 && snapshotPtr > 0);

function create(options, seed = 1n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function state(handle) {
  assert.equal(exports.nw_api_v1_read_state(handle, BigInt(statePtr), 112n), 112n);
  const view = new DataView(instance.exports.memory.buffer, statePtr, 112);
  assert.equal(view.getUint32(0, true), 0x3152574e);
  assert.equal(view.getUint32(12, true), 12);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function info(handle, field) {
  return exports.nw_api_v1_nback3d_info(handle, BigInt(field));
}

function action(handle, code, timestamp, sequence) {
  return exports.nw_api_v1_dispatch(handle, EVENT_ACTION,
    BigInt(timestamp), BigInt(sequence), code, 0n, 0n, 0n, 0n, 0n, 0n);
}

function advance(handle, timestamp, elapsed, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), BigInt(elapsed),
    BigInt(sequence));
}

function frame(handle, black = 0n) {
  const length = exports.nw_api_v1_render(handle, BigInt(framePtr),
    FRAME_CAPACITY, black, 912n, 684n);
  assert.ok(length > 0n);
  return new Uint8Array(instance.exports.memory.buffer, framePtr,
    Number(length)).slice();
}

function commands(handle) {
  return decode(frame(handle));
}

function text(handle) {
  return commands(handle).filter(({ kind }) => kind === Kind.TEXT)
    .map(({ text: value }) => value);
}

assert.equal(Number(exports.nw_api_v1_abi_version()), 1);
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 1n, 24n, 3000n, 500n, 200n]), STATUS.badOptions,
  "N must be positive");
assert.equal(create([2n, 1n, 3n, 3000n, 500n, 200n]), STATUS.badOptions,
  "the common API keeps the source's four-trial minimum");
assert.equal(create([2n, 1n, 24n, 50n, 500n, 200n]), STATUS.badOptions,
  "trial intervals shorter than the source scheduler floor are rejected");

// The default port route is the source's 3D position mode: N=2, one cube,
// twenty base trials plus N² priming trials, and the stock 3/0.5/0.2 second
// phase durations.
const run = create([2n, 1n, 24n, 3000n, 500n, 200n], 17n);
assert.ok(run > 0n);
assert.deepEqual(state(run), [0n, 2n, 0n, 24n, 1n, 0n, 0n, -1n,
  0n, 0n, 0n, 0n]);
assert.equal(info(run, INFO.interval), 3000n);
assert.equal(info(run, INFO.stimulus), 500n);
assert.equal(info(run, INFO.feedback), 200n);
assert.equal(info(run, INFO.seed), 17n);
assert.equal(info(run, INFO.error), 0n);
assert.ok(text(run).some((value) => value === "3D N-Back"));

const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame,
  "render is observational and byte-stable before the run starts");
assert.equal(action(run, ACTION.match, 100n, 0n), STATUS.ignored,
  "a match cannot be reported before the first stimulus");
assert.equal(action(run, ACTION.start, 100n, 1n), STATUS.accepted);
let values = state(run);
assert.equal(values[FIELD.phase], PHASE.startup,
  "the source has a blank startup interval before trial one");
assert.equal(values[FIELD.trial], 0n);
assert.equal(info(run, INFO.deadline), 1100n);
assert.equal(advance(run, 1099n, 999n, 2n), STATUS.ignored,
  "startup remains blank until its tenth 100 ms scheduler wake-up");
assert.equal(advance(run, 1100n, 1n, 3n), STATUS.accepted);
values = state(run);
assert.equal(values[FIELD.phase], PHASE.stimulus);
assert.equal(values[FIELD.trial], 1n);
assert.equal(values[FIELD.position], 5n,
  "the default one-cube stream matches the source generator");
assert.ok(values[FIELD.position] >= 1n && values[FIELD.position] <= 6n,
  "one cube has one of six source face-pattern positions");
assert.ok(values[FIELD.color] >= 1n && values[FIELD.color] <= 8n,
  "one cube has one of eight source face-pattern colours");
assert.equal(info(run, INFO.deadline), 1600n);
const stimulusFrame = frame(run);
assert.deepEqual(frame(run), stimulusFrame,
  "rendering the visible stimulus does not consume or mutate the stream");
assert.ok(commands(run).some(({ kind }) => kind === Kind.POLYGON),
  "the live controller renders the 3D cube/pattern scene");

assert.equal(advance(run, 1599n, 499n, 4n), STATUS.ignored,
  "an early tick cannot hide the stimulus");
assert.equal(advance(run, 1600n, 1n, 5n), STATUS.accepted);
values = state(run);
assert.equal(values[FIELD.phase], PHASE.response);
assert.equal(values[FIELD.position], 0n);
assert.equal(values[FIELD.color], 0n);
assert.equal(action(run, ACTION.match, 1601n, 6n), STATUS.accepted,
  "the match action is accepted throughout the response window");
values = state(run);
assert.equal(values[FIELD.answered], 1n);
assert.equal(values[FIELD.verdict], 0n,
  "the first N=2 trial is necessarily a false alarm when answered");
assert.equal(values[FIELD.falseAlarms], 1n);
assert.equal(action(run, ACTION.match, 1602n, 7n), STATUS.ignored,
  "a second response in one trial cannot double-score it");

assert.equal(advance(run, 3900n, 2300n, 8n), STATUS.accepted,
  "feedback begins before the trial deadline");
values = state(run);
assert.equal(values[FIELD.phase], PHASE.feedback);
assert.equal(values[FIELD.position], 0n);
assert.ok(text(run).some((value) => value === "False alarm"));
assert.equal(advance(run, 4100n, 200n, 9n), STATUS.accepted,
  "the next stimulus starts exactly at the trial deadline");
values = state(run);
assert.equal(values[FIELD.phase], PHASE.stimulus);
assert.equal(values[FIELD.trial], 2n);

// Pause freezes the logical phase and deadline; resume restores the same
// phase with the remaining duration, rather than restarting the stimulus.
assert.equal(action(run, ACTION.pause, 4200n, 10n), STATUS.accepted);
assert.equal(state(run)[FIELD.phase], PHASE.paused);
assert.equal(info(run, INFO.paused), 1n);
assert.equal(info(run, INFO.deadline), 0n);
assert.equal(advance(run, 9800n, 5600n, 11n), STATUS.ignored);
assert.equal(action(run, ACTION.pause, 9800n, 12n), STATUS.accepted);
assert.equal(state(run)[FIELD.phase], PHASE.stimulus);
assert.equal(info(run, INFO.paused), 0n);
assert.ok(info(run, INFO.deadline) > 9000n);
assert.equal(action(run, ACTION.restart, 10000n, 13n), STATUS.accepted);
assert.deepEqual(state(run).slice(0, 5), [PHASE.startup, 2n, 0n, 24n, 1n]);
assert.equal(advance(run, 11000n, 1000n, 14n), STATUS.accepted);
assert.deepEqual(state(run).slice(0, 5), [PHASE.stimulus, 2n, 1n, 24n, 1n]);
assert.equal(info(run, INFO.error), 0n);

// N-Back's fixed-layout controller can be copied by the common versioned
// snapshot ABI. The saved state is taken during a live stimulus, so restore
// must preserve the generated position/colour and timing phase rather than
// merely returning an equivalent ready screen.
const beforeSnapshot = state(run);
const snapshotBytes = exports.nw_api_v1_snapshot(
  run, BigInt(snapshotPtr), FRAME_CAPACITY);
assert.ok(snapshotBytes > 16n);
const restored = exports.nw_api_v1_restore(BigInt(snapshotPtr), snapshotBytes);
assert.ok(restored > run);
assert.deepEqual(state(restored), beforeSnapshot,
  "restored 3D N-Back state preserves the live stimulus");
assert.deepEqual(frame(restored), frame(run),
  "restored 3D N-Back frame preserves the visible cube");
assert.equal(exports.nw_api_v1_destroy(restored), 0n);
assert.equal(exports.nw_api_v1_destroy(run), 0n);

// A two-cube run uses the full 36-position/64-colour source domains. With
// feedback disabled, drive all four trials from the visible positions and
// answer exactly when the current position equals the N-back history value.
const replay = create([2n, 2n, 4n, 3000n, 500n, 0n], 12345n);
assert.ok(replay > run);
assert.equal(action(replay, ACTION.start, 0n, 0n), STATUS.accepted);
assert.equal(advance(replay, 999n, 999n, 1n), STATUS.ignored);
assert.equal(advance(replay, 1000n, 1n, 2n), STATUS.accepted);
const history = [];
const expectedPositions = [27n, 36n, 22n, 22n];
const expectedColors = [1n, 1n, 1n, 1n];
let expectedHits = 0n;
let expectedMisses = 0n;
let expectedCorrectRejections = 0n;
let nextSequence = 3n;
for (let index = 0; index < 4; index += 1) {
  const trialStart = 1000 + index * 3000;
  values = state(replay);
  assert.equal(values[FIELD.phase], PHASE.stimulus);
  const position = values[FIELD.position];
  const color = values[FIELD.color];
  assert.equal(position, expectedPositions[index],
    "the 2-cube position stream matches the source generator");
  assert.equal(color, expectedColors[index],
    "the position-only source mode keeps its configured face colour");
  assert.ok(position >= 1n && position <= 36n);
  assert.ok(color >= 1n && color <= 64n);
  history.push(position);
  const match = index >= 2 && position === history[index - 2];
  if (match) {
    expectedHits += 1n;
    assert.equal(action(replay, ACTION.match, trialStart + 1, nextSequence++), STATUS.accepted);
  } else {
    expectedCorrectRejections += 1n;
  }
  assert.equal(advance(replay, trialStart + 500, 500, nextSequence++), STATUS.accepted);
  assert.equal(advance(replay, trialStart + 3000, 2500, nextSequence++), STATUS.accepted);
  if (index < 3) {
    assert.equal(state(replay)[FIELD.phase], PHASE.stimulus);
  }
}
values = state(replay);
assert.equal(values[FIELD.phase], PHASE.done);
assert.equal(values[FIELD.hits], expectedHits);
assert.equal(values[FIELD.misses], expectedMisses);
assert.equal(info(replay, 12), expectedCorrectRejections);
assert.equal(values[FIELD.falseAlarms], 0n);
assert.equal(info(replay, INFO.error), 0n);
assert.equal(exports.nw_api_v1_destroy(replay), 0n);

console.log("nback3d_game_smoke: PASS (3D-only controller, source domains, lifecycle timing, masking, pause, grading, completion)");
