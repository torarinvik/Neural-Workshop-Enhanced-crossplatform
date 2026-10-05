// Common-v1 lifecycle smoke for source-backed Overrun.
// The test types the exact wave exposed by the controller, so success proves
// the source layout, letter buffer, timed settlement, result table, and
// display scene are connected rather than merely that a card was selected.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_overrun());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, text: 8n });
const KEY = Object.freeze({ space: 1n, enter: 2n, undo: 8n });
const ACTION = Object.freeze({ start: 0n, write: 1n, erase: 2n });
const PHASE = Object.freeze({ ready: 0n, typing: 1n, settled: 2n, done: 3n });
const INFO = Object.freeze({
  phase: 0, rung: 1, trial: 2, totalWaves: 3, wordCount: 4, length: 5,
  letters: 6, cleared: 7, typedCount: 8, driftMilli: 9, lives: 10,
  landed: 11, missed: 12, secondsMs: 13, untilMs: 14, verdict: 15,
  resultCount: 16, wpm: 17, bestRung: 18, stocked: 19, clockMs: 20,
});
const VALUE = Object.freeze({
  wordStart: 0n, wordLength: 1n, letterStart: 2n, waveLetter: 3n,
  typedLetter: 4n, resultRung: 100n, resultDone: 101n,
  resultWords: 102n, resultTookMs: 103n,
});
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [4n, 3n, 1n, 0n, 0n, 0n], seed = 17n) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, seed);
}
function dispatch(handle, kind, timestamp, sequence, code, value = 0n) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(timestamp),
    BigInt(sequence), code, value, 0n, 0n, 0n, 0n, 0n);
}
function action(handle, code, timestamp, sequence, value = 0n) {
  return dispatch(handle, EVENT.action, timestamp, sequence, code, value);
}
function keyDown(handle, key, timestamp, sequence) {
  return dispatch(handle, EVENT.keyDown, timestamp, sequence, key);
}
function text(handle, character, timestamp, sequence) {
  return dispatch(handle, EVENT.text, timestamp, sequence, 0n,
    BigInt(character.codePointAt(0)));
}
function advance(handle, timestamp, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), 0n, BigInt(sequence));
}
function info(handle, field) {
  return BigInt(exports.nw_api_v1_overrun_info(handle, BigInt(field)));
}
function value(handle, field, at = 0) {
  return BigInt(exports.nw_api_v1_overrun_value(handle, field, BigInt(at)));
}
function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}
function textIn(bytes, expected) {
  return decode(bytes).some(({ kind, text: shown }) =>
    kind === Kind.TEXT && shown.includes(expected));
}

assert.equal(TASK, 1156693128n, "Overrun keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([0n, 1n, 1n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([4n, 4n, 1n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([4n, 1n, 2n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create([4n, 1n, 1n, 1n, 0n, 0n]), STATUS.badOptions);

const run = create();
const replay = create();
assert.ok(run > 0n && replay > 0n);
assert.equal(info(run, INFO.phase), PHASE.ready);
assert.equal(info(run, INFO.stocked), 0n);
assert.ok(textIn(frame(run), "Overrun"));
assert.ok(textIn(frame(run), "Press Space to start"));

// Keyboard Space and the explicit action must create identical source waves.
assert.equal(keyDown(run, KEY.space, 0, 0), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 0, 0), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.typing);
assert.equal(info(run, INFO.trial), 1n);
assert.ok(info(run, INFO.wordCount) >= 6n);
assert.equal(info(run, INFO.wordCount), info(replay, INFO.wordCount));
assert.equal(info(run, INFO.length), info(replay, INFO.length));
assert.equal(info(run, INFO.letters), info(replay, INFO.letters));
assert.ok(textIn(frame(run), "wave 1/3"));

// Type the exact source answer through two different host paths: action ABI
// for one run, EVENT_TEXT for the replay.  A wrong key is sticky until erase.
assert.equal(action(run, ACTION.write, 1, 1, 25n), STATUS.accepted);
assert.equal(info(run, INFO.typedCount), 1n);
assert.equal(action(run, ACTION.erase, 2, 2), STATUS.accepted);
assert.equal(info(run, INFO.typedCount), 0n);
let sequence = 3;
let textSequence = 1;
let now = 3;
for (let word = 0n; word < info(run, INFO.wordCount); word += 1n) {
  const start = value(run, VALUE.letterStart, Number(word));
  const width = value(run, VALUE.wordLength, Number(word));
  for (let step = 0n; step < width; step += 1n) {
    const letter = value(run, VALUE.waveLetter, Number(start + step));
    assert.ok(letter >= 0n && letter < 26n);
    assert.equal(action(run, ACTION.write, now, sequence, letter), STATUS.accepted);
    assert.equal(text(replay, String.fromCharCode(Number(letter) + 97), now, textSequence), STATUS.accepted);
    sequence += 1;
    textSequence += 1;
    now += 1;
  }
}
assert.equal(info(run, INFO.phase), PHASE.settled);
assert.equal(info(run, INFO.verdict), 1n);
assert.equal(info(run, INFO.resultCount), 1n);
assert.equal(info(run, INFO.cleared), info(replay, INFO.cleared));
assert.equal(value(run, VALUE.resultDone, 0), 1n);
assert.equal(value(run, VALUE.resultWords, 0), info(run, INFO.wordCount));
assert.ok(textIn(frame(run), "Clear"));

const until = info(run, INFO.untilMs);
assert.equal(advance(run, until - 1n, sequence), STATUS.ignored);
assert.equal(info(run, INFO.phase), PHASE.settled);
assert.equal(advance(run, until, sequence + 1), STATUS.accepted);
assert.equal(advance(replay, until, textSequence + 1), STATUS.accepted);
assert.equal(info(run, INFO.phase), PHASE.typing);
assert.equal(info(replay, INFO.phase), PHASE.typing);

// The source option set deliberately has a minimum of three waves.  Drive
// the remaining two through the real deadline path instead of weakening the
// controller's source-compatible validation just to make this smoke short:
// each advance is clamped to a 100 ms physics step by Overrun::update.
let timeoutNow = Number(until);
let timeoutSequence = sequence + 2;
for (let wave = 2; wave <= 3; wave += 1) {
  let guard = 0;
  while (info(run, INFO.phase) === PHASE.typing && guard < 200) {
    timeoutNow += 1000;
    assert.equal(advance(run, timeoutNow, timeoutSequence), STATUS.accepted);
    assert.equal(advance(replay, timeoutNow, timeoutSequence), STATUS.accepted);
    timeoutSequence += 1;
    guard += 1;
  }
  assert.equal(info(run, INFO.phase), PHASE.settled);
  assert.equal(info(replay, INFO.phase), PHASE.settled);
  const nextUntil = info(run, INFO.untilMs);
  assert.equal(advance(run, nextUntil, timeoutSequence), STATUS.accepted);
  assert.equal(advance(replay, nextUntil, timeoutSequence), STATUS.accepted);
  timeoutSequence += 1;
  if (wave < 3) {
    assert.equal(info(run, INFO.phase), PHASE.typing);
    assert.equal(info(replay, INFO.phase), PHASE.typing);
  }
}
assert.equal(info(run, INFO.phase), PHASE.done);
assert.equal(info(replay, INFO.phase), PHASE.done);
assert.equal(info(run, INFO.resultCount), 3n);
assert.ok(textIn(frame(run), "Run complete"));

for (const handle of [run, replay]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Overrun source-backed seed pool, typing, rub-out, timing, scoring, rendering, options, and cleanup");
