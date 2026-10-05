// Common-v1 lifecycle and render checks for the stateful Count controller.
// Generation itself is separately compared to the Python source in
// counting_diff.py; this test verifies that the actual menu-facing run uses it.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const task = BigInt(exports.nw_api_v1_task_count());
const ptr = Number(exports.nw_frame_alloc(65536n));
const statePtr = Number(exports.nw_frame_alloc(112n));
assert.ok(task > 0n && ptr > 0 && statePtr > 0);

const EVENT = { action: 1n, keyDown: 2n, text: 8n };
const KEY = { space: 1n, enter: 2n };
const ACTION = { start: 0n, digit: 1n, backspace: 2n, submit: 3n };
const PHASE = { ready: 0n, showing: 1n, hidden: 2n, feedback: 3n, done: 4n };
const FIELD = { phase: 0, kind: 1, count: 2, trial: 3, trials: 4,
  correct: 5, answer: 6, answerLength: 7, shown: 8, verdict: 9,
  adaptive: 10, deadline: 11 };
const STATUS = { accepted: 1n, ignored: 2n, badOptions: -3n,
  badEvent: -6n, eventOrder: -7n };

function create(options, seed = 17n) {
  return exports.nw_api_v1_create(task, 1n, ...options, seed);
}
function state(handle) {
  const length = exports.nw_api_v1_read_state(handle, BigInt(statePtr), 112n);
  assert.equal(length, 112n);
  const view = new DataView(instance.exports.memory.buffer, statePtr, 112);
  assert.equal(view.getUint32(0, true), 0x3152574e);
  assert.equal(view.getUint32(12, true), 12);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}
function event(handle, kind, timestamp, sequence, code, value = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, timestamp, sequence,
    code, value, 0n, 0n, 0n, 0n, 0n);
}
function action(handle, code, value, timestamp, sequence) {
  return event(handle, EVENT.action, BigInt(timestamp), BigInt(sequence),
    code, value);
}
function text(handle, character, timestamp, sequence) {
  return event(handle, EVENT.text, BigInt(timestamp), BigInt(sequence), 0n,
    BigInt(character.codePointAt(0)));
}
function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(ptr), 65536n,
    0n, 912n, 684n);
  assert.ok(length > 0n, `Count render succeeds (${length})`);
  return decode(new Uint8Array(instance.exports.memory.buffer, ptr,
    Number(length)).slice());
}
function shapeCommands(commands) {
  return commands.filter(({ kind }) => [Kind.LINE, Kind.ARC, Kind.BOX,
    Kind.MULTILINE].includes(kind));
}

assert.equal(Number(exports.nw_api_v1_abi_version()), 1);
assert.equal(Number(exports.nw_api_v1_supports(task)), 1);
assert.equal(create([0n, 7n, 5n, 0n, 1n, 1n]), STATUS.badOptions,
  "starting shape count must be one of the original option values");
assert.equal(create([0n, 8n, 4n, 0n, 1n, 1n]), STATUS.badOptions,
  "trial count must be one of the original option values");
assert.equal(create([0n, 8n, 5n, 100n, 1n, 1n]), STATUS.badOptions,
  "exposure must be one of the original option values");
assert.equal(create([0n, 8n, 5n, 0n, 2n, 1n]), STATUS.badOptions,
  "adaptive is boolean");

// Full timed/adaptive route: leading-zero normalization, correct grading,
// visible feedback, deadline transition, hidden exposure, and backspace.
const run = create([0n, 8n, 5n, 200n, 1n, 1n], 17n);
assert.ok(run > 0n);
assert.deepEqual(state(run), [0n, 0n, 8n, 0n, 5n, 0n, 0n, 0n, 0n, -1n, 1n, 0n]);
assert.equal(action(run, ACTION.submit, 0n, 999, 0), STATUS.ignored,
  "empty submit is ignored without starting a round");
assert.equal(action(run, ACTION.start, 0n, 1000, 1), STATUS.accepted);
let values = state(run);
assert.equal(values[FIELD.phase], PHASE.showing);
assert.equal(values[FIELD.trial], 1n);
assert.equal(values[FIELD.shown], 8n);
assert.equal(values[FIELD.deadline], 1200n);
assert.equal(shapeCommands(frame(run)).length, 8,
  "the actual eight generated line shapes are rendered");
const stableFrame = frame(run);
assert.deepEqual(frame(run), stableFrame, "render does not consume randomness or mutate state");
assert.equal(exports.nw_api_v1_advance(run, 1199n, 199n, 2n), STATUS.ignored,
  "an early clock advance does not hide the tangle");
assert.equal(text(run, "0", 1199n, 3), STATUS.accepted);
assert.equal(text(run, "8", 1199n, 4), STATUS.accepted);
values = state(run);
assert.equal(values[FIELD.answer], 8n, "leading zeroes are stripped as in the source");
assert.equal(values[FIELD.answerLength], 1n);
assert.equal(event(run, EVENT.keyDown, 1200n, 5n, KEY.enter, 13n), STATUS.accepted);
values = state(run);
assert.equal(values[FIELD.phase], PHASE.feedback);
assert.equal(values[FIELD.correct], 1n);
assert.equal(values[FIELD.count], 9n, "adaptive success increases the next trial");
assert.equal(values[FIELD.verdict], 1n);
assert.equal(values[FIELD.deadline], 2000n);
assert.ok(frame(run).some(({ kind, text: label }) =>
  kind === Kind.TEXT && label === "Yes, 9"));
assert.equal(exports.nw_api_v1_advance(run, 1999n, 799n, 6n), STATUS.ignored);
assert.equal(exports.nw_api_v1_advance(run, 2000n, 1n, 7n), STATUS.accepted);
values = state(run);
assert.equal(values[FIELD.phase], PHASE.showing);
assert.equal(values[FIELD.trial], 2n);
assert.equal(values[FIELD.shown], 9n);
assert.equal(values[FIELD.deadline], 2200n);
assert.equal(exports.nw_api_v1_advance(run, 2200n, 200n, 8n), STATUS.accepted);
assert.equal(state(run)[FIELD.phase], PHASE.hidden);
assert.equal(shapeCommands(frame(run)).length, 0,
  "expired exposure hides every shape but keeps the answer scene live");
assert.equal(text(run, "0", 2201n, 9), STATUS.accepted);
assert.equal(text(run, "9", 2201n, 10), STATUS.accepted);
assert.equal(state(run)[FIELD.answer], 9n);
assert.equal(action(run, ACTION.backspace, 0n, 2202, 11), STATUS.accepted);
assert.equal(state(run)[FIELD.answerLength], 0n,
  "backspace removes the final normalized digit");
assert.equal(text(run, "9", 2202n, 12), STATUS.accepted);
assert.equal(action(run, ACTION.submit, 0n, 2203, 13), STATUS.accepted);
assert.equal(state(run)[FIELD.correct], 2n);
assert.equal(state(run)[FIELD.count], 10n);
assert.equal(exports.nw_api_v1_destroy(run), 0n);
assert.equal(exports.nw_api_v1_destroy(run), 0n,
  "common v1 destroy remains idempotent for Count");

// With feedback disabled, submit deals the next round immediately. The
// controller does not expose a transient answer/verdict frame.
const immediate = create([1n, 2n, 5n, 0n, 0n, 0n], 4n);
assert.ok(immediate > run);
assert.equal(action(immediate, ACTION.start, 0n, 50, 0), STATUS.accepted);
assert.equal(shapeCommands(frame(immediate)).filter(({ kind }) => kind === Kind.ARC).length,
  2, "the circles option routes through the real Count renderer");
assert.equal(action(immediate, ACTION.digit, 1n, 51, 1), STATUS.accepted);
assert.equal(action(immediate, ACTION.submit, 0n, 52, 2), STATUS.accepted);
values = state(immediate);
assert.equal(values[FIELD.phase], PHASE.showing);
assert.equal(values[FIELD.trial], 2n);
assert.equal(values[FIELD.verdict], -1n);
assert.equal(values[FIELD.count], 2n, "non-adaptive mode retains its starting count");

// Dense mixed generation reaches the real upper bound and remains renderable.
const dense = create([4n, 60n, 5n, 0n, 0n, 1n], 99n);
assert.ok(dense > immediate);
assert.equal(action(dense, ACTION.start, 0n, 100, 0), STATUS.accepted);
assert.equal(shapeCommands(frame(dense)).length, 60,
  "all sixty mixed generated outlines are present in the display list");

// Finish a complete run and replay from DONE; the fixed seed stream continues
// across runs while per-run score/adaptation resets to the configured start.
const complete = create([3n, 2n, 5n, 0n, 0n, 1n], 21n);
assert.ok(complete > dense);
let time = 1000;
let sequence = 0;
for (let trial = 1; trial <= 5; trial++) {
  if (trial === 1) {
    assert.equal(action(complete, ACTION.start, 0n, time, sequence++), STATUS.accepted);
  } else {
    assert.equal(state(complete)[FIELD.phase], PHASE.showing,
      "feedback expiry has already dealt the next trial");
  }
  assert.equal(action(complete, ACTION.digit, 2n, time + 1, sequence++), STATUS.accepted);
  assert.equal(action(complete, ACTION.submit, 0n, time + 2, sequence++), STATUS.accepted);
  assert.equal(state(complete)[FIELD.correct], BigInt(trial));
  time += 802;
  assert.equal(exports.nw_api_v1_advance(complete, BigInt(time), 800n,
    BigInt(sequence++)), STATUS.accepted);
  time += 1;
}
values = state(complete);
assert.equal(values[FIELD.phase], PHASE.done);
assert.equal(values[FIELD.trial], 5n);
assert.equal(values[FIELD.correct], 5n);
assert.equal(shapeCommands(frame(complete)).length, 0);
assert.ok(frame(complete).some(({ kind, text: label }) =>
  kind === Kind.TEXT && label === "100% — 5 of 5, average error 0.0"));
assert.equal(event(complete, EVENT.keyDown, BigInt(time), BigInt(sequence++),
  KEY.space, 32n), STATUS.accepted, "Space replays a completed run");
assert.equal(state(complete)[FIELD.phase], PHASE.showing);
assert.equal(state(complete)[FIELD.trial], 1n);
assert.equal(state(complete)[FIELD.correct], 0n);

for (const handle of [immediate, dense, complete]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
}

console.log("counting_game_smoke: PASS (common lifecycle, source options, typed input, exposure, adaptive scoring, dense render, completion/replay)");
