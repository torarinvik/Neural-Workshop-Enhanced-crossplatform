// Common-v1 lifecycle smoke for the source-backed Concentration controller.
// Card placement and matching are inspected only to choose legal probes; all
// transitions still go through the common action/pointer/advance ABI.
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = BigInt(exports.nw_api_v1_task_concentration());
const STATUS = Object.freeze({ accepted: 1n, ignored: 2n, badOptions: -3n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerDown: 5n });
const KEY = Object.freeze({ space: 1n, enter: 2n });
const ACTION = Object.freeze({ start: 0n, select: 1n });
const PHASE = Object.freeze({ ready: 0n, peek: 1n, playing: 2n, done: 3n });
const INFO = Object.freeze({
  phase: 0, pairs: 1, count: 2, medium: 3, turns: 4, lapses: 5,
  flippedCount: 6, matchedPairs: 7, verdict: 8, cursor: 9,
  showTurns: 10, coach: 11, peekUntilMs: 12, hideUntilMs: 13,
  startedAtMs: 14, finishedAtMs: 15,
});
const CARD = Object.freeze({ index: 0n, faceUp: 1n, matched: 2n });
const STATE_BYTES = 112;
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE_BYTES)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(TASK > 0n && STATE_BUFFER > 0 && FRAME_BUFFER > 0);

function create(options = [8n, 0n, 0n, 900n, 1n, 0n], seed = 17n) {
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

function info(handle, field) {
  return BigInt(exports.nw_api_v1_concentration_info(handle, BigInt(field)));
}

function card(handle, field, at) {
  return BigInt(exports.nw_api_v1_concentration_card(handle, field, BigInt(at)));
}

function frame(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    BigInt(FRAME_BYTES), 0n, 912n, 684n);
  assert.ok(length > 0n, `render failed: ${length}`);
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

function layout(count, pairs) {
  const width = 912;
  const floor = 179;
  const ceiling = 596;
  const room = Math.max(80, ceiling - floor);
  const aspect = Math.max(0.2, width * 0.9 / room);
  let columns = Math.max(2, Math.min(count,
    Math.round(Math.sqrt(count * aspect))));
  let rows = Math.ceil(count / columns);
  while (columns * rows - count >= rows && columns > 2) {
    columns -= 1;
    rows = Math.ceil(count / columns);
  }
  const spanW = width * 0.9;
  const spanH = room;
  const gap = Math.max(4, Math.min(spanW / columns, spanH / rows) * 0.09);
  const side = Math.min(
    (spanW - gap * (columns - 1)) / columns,
    (spanH - gap * (rows - 1)) / rows,
  );
  const totalW = side * columns + gap * (columns - 1);
  const totalH = side * rows + gap * (rows - 1);
  const left = (width - totalW) / 2;
  const top = floor + totalH + (spanH - totalH) / 2;
  return { columns, left, top, side, gap, pairs };
}

function pointerAt(handle, plan, position, timestamp, sequence) {
  const column = position % plan.columns;
  const row = Math.floor(position / plan.columns);
  const x = plan.left + column * (plan.side + plan.gap) + plan.side / 2;
  const y = plan.top - (row + 0.5) * plan.side - row * plan.gap;
  return event(handle, EVENT.pointerDown, timestamp, sequence, 0n, 0n,
    BigInt(Math.round(x * 1000000 / 912)),
    BigInt(Math.round(y * 1000000 / 684)));
}

function findPair(handle, count, excluded = new Set()) {
  const seen = new Map();
  for (let at = 0; at < count; at += 1) {
    if (excluded.has(at) || card(handle, CARD.matched, at) !== 0n) continue;
    const pair = Number(card(handle, CARD.index, at));
    const first = seen.get(pair);
    if (first !== undefined) return [first, at];
    seen.set(pair, at);
  }
  return null;
}

assert.equal(TASK, 1179922742n, "Concentration keeps its stable task ID");
assert.equal(Number(exports.nw_api_v1_supports(TASK)), 1);
assert.equal(create([3n, 0n, 0n, 900n, 1n, 0n]), STATUS.badOptions);
assert.equal(create([8n, 2n, 0n, 900n, 1n, 0n]), STATUS.badOptions);
assert.equal(create([8n, 0n, 250n, 900n, 1n, 0n]), STATUS.badOptions);
assert.equal(create([8n, 0n, 0n, 100n, 1n, 0n]), STATUS.badOptions);
assert.equal(create([8n, 0n, 0n, 900n, 2n, 0n]), STATUS.badOptions);

const run = create([4n, 0n, 0n, 300n, 1n, 0n], 17n);
const replay = create([4n, 0n, 0n, 300n, 1n, 0n], 17n);
assert.ok(run > 0n && replay > 0n);
assert.deepEqual(state(run), [0n, 4n, 0n, 0n, 0n, 0n, 0n, 0n, -1n, 0n, 1n, 0n]);
const readyFrame = frame(run);
assert.deepEqual(frame(run), readyFrame, "ready rendering is observational");
assert.ok(decode(readyFrame).some(({ kind, text }) =>
  kind === Kind.TEXT && text === "Concentration"));

assert.equal(event(run, EVENT.keyDown, 100, 0, KEY.enter, 13n), STATUS.accepted);
assert.equal(action(replay, ACTION.start, 100, 0), STATUS.accepted);
assert.deepEqual(state(run), state(replay), "same seed gives the same deal");
assert.equal(info(run, INFO.phase), PHASE.playing);
assert.equal(info(run, INFO.count), 8n);
for (let at = 0; at < 8; at += 1) {
  assert.equal(card(run, CARD.faceUp, at), 0n);
  assert.equal(card(run, CARD.index, at), card(replay, CARD.index, at));
}
const plan = layout(8, 4);
assert.ok(frame(run).length > 0);

const pair = findPair(run, 8);
assert.ok(pair);
assert.equal(pointerAt(run, plan, pair[0], 101, 1), STATUS.accepted);
assert.equal(info(run, INFO.flippedCount), 1n);
assert.equal(pointerAt(run, plan, pair[1], 102, 2), STATUS.accepted);
assert.equal(info(run, INFO.matchedPairs), 1n);
assert.equal(info(run, INFO.turns), 1n);
assert.equal(info(run, INFO.flippedCount), 0n);

const mismatchFirst = findPair(run, 8, new Set(pair));
assert.ok(mismatchFirst);
const different = mismatchFirst[0];
let second = -1;
for (let at = 0; at < 8; at += 1) {
  if (at !== different && card(run, CARD.index, at) !== card(run, CARD.index, different) &&
      card(run, CARD.matched, at) === 0n) {
    second = at;
    break;
  }
}
assert.ok(second >= 0);
assert.equal(pointerAt(run, plan, different, 103, 3), STATUS.accepted);
assert.equal(pointerAt(run, plan, second, 104, 4), STATUS.accepted);
assert.equal(info(run, INFO.flippedCount), 2n);
assert.equal(info(run, INFO.turns), 2n);
const hideAt = info(run, INFO.hideUntilMs);
assert.ok(hideAt >= 404n);
assert.equal(exports.nw_api_v1_advance(run, hideAt, 300n, 5n), STATUS.accepted);
assert.equal(info(run, INFO.flippedCount), 0n);
assert.equal(card(run, CARD.faceUp, different), 0n);
assert.equal(card(run, CARD.faceUp, second), 0n);

// A nonzero peek is source-compatible for picture cards and is settled only
// by advance; sound cards skip the peek because a sound cannot be previewed.
const peek = create([4n, 0n, 500n, 300n, 1n, 0n], 19n);
assert.equal(action(peek, ACTION.start, 200, 0), STATUS.accepted);
assert.equal(info(peek, INFO.phase), PHASE.peek);
assert.equal(info(peek, INFO.peekUntilMs), 700n);
assert.equal(exports.nw_api_v1_advance(peek, 699n, 499n, 1n), STATUS.ignored);
assert.equal(info(peek, INFO.phase), PHASE.peek);
assert.equal(exports.nw_api_v1_advance(peek, 700n, 500n, 2n), STATUS.accepted);
assert.equal(info(peek, INFO.phase), PHASE.playing);
const sound = create([4n, 1n, 500n, 300n, 1n, 0n], 19n);
assert.equal(action(sound, ACTION.start, 200, 0), STATUS.accepted);
assert.equal(info(sound, INFO.phase), PHASE.playing);

for (const handle of [run, replay, peek, sound]) {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
  assert.equal(exports.nw_api_v1_destroy(handle), 0n, "destroy is idempotent");
}

console.log("PASS: Concentration source-backed deal, identity scoring, timed phases, pointer selection, rendering, options, and cleanup");
