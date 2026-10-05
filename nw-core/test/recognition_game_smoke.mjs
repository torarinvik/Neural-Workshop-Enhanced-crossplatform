// Common-v1 lifecycle smoke for the source-backed Seen It Before? controller.
// The source task's filesystem media pool is intentionally replaced by stable
// synthetic identities in the WASM controller; all sequencing, repeat rules,
// answer scoring, timed hiding, feedback, and input routing are exercised here.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_recognition());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerDown: 5n });
const KEY = Object.freeze({ space: 1n, enter: 2n, left: 3n, right: 5n, restart: 9n });
const ACTION = Object.freeze({ start: 0n, seen: 1n, newItem: 2n, replay: 3n });
const PHASE = Object.freeze({ ready: 0n, showing: 1n, hidden: 2n, feedback: 3n, done: 4n });
const INFO = Object.freeze({
  phase: 0, totalTrials: 1, index: 2, medium: 3, repeatPercent: 4,
  minLag: 5, studyMs: 6, feedback: 7, item: 8, repeat: 9,
  lastCorrect: 10, shownAtMs: 11, deadlineMs: 12, hits: 13, misses: 14,
  falseAlarms: 15, correctRejections: 16, answered: 17, asset: 18,
});
const ITEM = Object.freeze({ id: 0n, repeat: 1n, answered: 2n, choice: 3n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [40n, 0n, 40n, 4n, 0n, 1n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}

function state(handle) {
  const length = exports.nw_api_v1_read_state(handle,
    BigInt(STATE_BUFFER), BigInt(STATE_BYTES));
  assert.equal(length, BigInt(STATE_BYTES));
  const view = new DataView(instance.exports.memory.buffer, STATE_BUFFER, STATE_BYTES);
  assert.equal(view.getUint32(0, true), 0x3152574e);
  assert.equal(view.getUint32(4, true), 1);
  assert.equal(view.getUint32(12, true), 12);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function event(handle, kind, timestamp, sequence, code, value = 0n,
               x = 0n, y = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, x, y, 0n);
}

function action(handle, code, timestamp, sequence, value = 0n) {
  return event(handle, EVENT.action, timestamp, sequence, code, value);
}

function keyDown(handle, key, timestamp, sequence) {
  return event(handle, EVENT.keyDown, timestamp, sequence, key);
}

function advance(handle, timestamp, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), 0n, BigInt(sequence));
}

function info(handle, field) {
  return BigInt(exports.nw_api_v1_recognition_info(handle, BigInt(field)));
}

function item(handle, field, at) {
  return BigInt(exports.nw_api_v1_recognition_item(handle, field, BigInt(at)));
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function buttonPointer(handle, right, timestamp, sequence) {
  const width = Math.min(912 * 0.24, 912 / 3.2);
  const height = Math.max(40, 684 * 0.075);
  const gap = 912 * 0.04;
  const bottom = 90;
  const left = (912 - (width * 2 + gap)) / 2;
  const x = left + (right ? width + gap : 0) + width / 2;
  const y = bottom + height / 2;
  return event(handle, EVENT.pointerDown, timestamp, sequence, 0n, 0n,
    BigInt(Math.round(x * 1000000 / 912)),
    BigInt(Math.round(y * 1000000 / 684)));
}

assert.equal(TASK, 3372563504n, "Seen It Before? keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([5n, 0n, 40n, 4n, 0n, 1n]), STATUS.badOptions);
assert.equal(create([40n, 2n, 40n, 4n, 0n, 1n]), STATUS.badOptions);
assert.equal(create([40n, 0n, 10n, 4n, 0n, 1n]), STATUS.badOptions);
assert.equal(create([40n, 0n, 40n, 0n, 0n, 1n]), STATUS.badOptions);
assert.equal(create([40n, 0n, 40n, 4n, 250n, 1n]), STATUS.badOptions);
assert.equal(create([40n, 0n, 40n, 4n, 0n, 2n]), STATUS.badOptions);

const run = create([10n, 0n, 50n, 1n, 0n, 1n], 17n);
const replay = create([10n, 0n, 50n, 1n, 0n, 1n], 17n);
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 10n, 0n, 0n, 50n, 1n, 0n, 1n, -1n, -1n, -1n, 0n]);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(decode(readyFrame).some(({ kind, text }) =>
  kind === Kind.TEXT && text === "Seen it before?"));

assert.equal(keyDown(run, KEY.space, 100, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.deepEqual(state(run), state(replay), "same seed gives the same planned run");
assert.equal(info(run, INFO.phase), PHASE.showing);
assert.equal(info(run, INFO.totalTrials), 10n);
assert.ok(info(run, INFO.item) >= 0n);
assert.ok(info(run, INFO.asset) >= 2000n);
assert.ok(decode(frame(run)).some(({ kind }) => kind === Kind.SPRITE));

// Drive the first answer through the source keyboard mapping, then complete
// the rest through the action ABI while checking feedback/deadline ordering.
let sequence = 1;
let now = 101;
let usedPointer = false;
while (info(run, INFO.phase) !== PHASE.done) {
  const phase = info(run, INFO.phase);
  if (phase === PHASE.showing || phase === PHASE.hidden) {
    const repeat = info(run, INFO.repeat) !== 0n;
    const expected = repeat ? ACTION.seen : ACTION.newItem;
    if (!usedPointer) {
      assert.equal(buttonPointer(run, expected === ACTION.newItem, now, sequence), STATUS.accepted);
      usedPointer = true;
    } else if (expected === ACTION.seen) {
      assert.equal(action(run, ACTION.seen, now, sequence), STATUS.accepted);
    } else {
      assert.equal(action(run, ACTION.newItem, now, sequence), STATUS.accepted);
    }
    const last = info(run, INFO.lastCorrect);
    assert.equal(last, 1n);
    sequence += 1;
    now += 1;
  } else if (phase === PHASE.feedback) {
    assert.equal(info(run, INFO.deadlineMs), BigInt(now + 350 - 1));
    now = Number(info(run, INFO.deadlineMs));
    assert.equal(advance(run, now, sequence), STATUS.accepted);
    sequence += 1;
    now += 1;
  } else {
    assert.fail(`unexpected phase ${phase}`);
  }
}
assert.equal(info(run, INFO.answered), 10n);
assert.equal(info(run, INFO.misses), 0n);
assert.equal(info(run, INFO.falseAlarms), 0n);
assert.equal(info(run, INFO.hits) + info(run, INFO.correctRejections), 10n);
for (let at = 0; at < 10; at += 1) {
  assert.equal(item(run, ITEM.answered, at), 1n);
  assert.ok(item(run, ITEM.id, at) >= 0n);
  assert.ok(item(run, ITEM.choice, at) === ACTION.seen ||
    item(run, ITEM.choice, at) === ACTION.newItem);
}

// A picture with a study interval changes to HIDDEN only at its deadline.
const timed = create([10n, 0n, 40n, 4n, 500n, 1n], 19n);
assert.equal(action(timed, ACTION.start, 200, 0), STATUS.accepted);
assert.equal(info(timed, INFO.phase), PHASE.showing);
assert.equal(info(timed, INFO.deadlineMs), 700n);
assert.equal(advance(timed, 699, 1), STATUS.ignored);
assert.equal(info(timed, INFO.phase), PHASE.showing);
assert.equal(advance(timed, 700, 2), STATUS.accepted);
assert.equal(info(timed, INFO.phase), PHASE.hidden);
assert.equal(action(timed, ACTION.newItem, 701, 3), STATUS.accepted);
assert.equal(info(timed, INFO.phase), PHASE.feedback);

// Sound has no visual study timeout and replay remains a legal source action.
const sound = create([10n, 1n, 40n, 4n, 500n, 1n], 19n);
assert.equal(action(sound, ACTION.start, 200, 0), STATUS.accepted);
assert.equal(info(sound, INFO.phase), PHASE.showing);
assert.equal(info(sound, INFO.deadlineMs), 0n);
assert.equal(advance(sound, 1000, 1), STATUS.ignored);
assert.equal(action(sound, ACTION.replay, 1001, 2), STATUS.accepted);
assert.equal(keyDown(sound, KEY.restart, 1002, 3), STATUS.accepted);

for (const handle of [run, replay, timed, sound]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Seen It Before source-backed planning, repeats, scoring, timed hiding, input, rendering, options, and cleanup");
