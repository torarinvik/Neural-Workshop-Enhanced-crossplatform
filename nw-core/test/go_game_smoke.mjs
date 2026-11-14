import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const wasm = process.env.NWCORE_WASM_PATH ?? fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const task = BigInt(exports.nw_api_v1_task_go_winning_move());
const ACTION = Object.freeze({ start: 0n, answer: 1n, next: 2n, level: 7n });
const INFO = Object.freeze({ phase: 0, difficulty: 1, trial: 2,
  totalTrials: 3, size: 4, cursorX: 5, cursorY: 6, correct: 7,
  verdict: 8, best: 9, captureOptions: 10, winning: 11, captured: 12 });
const VALUE_BOARD = 0n;
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, pointerDown: 5n });
const framePtr = Number(exports.nw_frame_alloc(1048576n));
let clock = 100;
let sequence = 0;

function create(level = 1, trials = 1, seed = 17) {
  const handle = exports.nw_api_v1_create(task, 1n, BigInt(level),
    BigInt(trials), 0n, 0n, 0n, 0n, BigInt(seed));
  assert.ok(handle > 0n, `Go create should accept ${level}/${trials}`);
  return handle;
}

function dispatch(handle, kind, code, value = 0, x = 0, y = 0) {
  return exports.nw_api_v1_dispatch(handle, kind, BigInt(clock++),
    BigInt(sequence++), BigInt(code), BigInt(value), 0n, 0n,
    BigInt(x), BigInt(y), 0n);
}

function info(handle, field) {
  return Number(exports.nw_api_v1_go_info(handle, BigInt(field)));
}

function value(handle, field, at) {
  return Number(exports.nw_api_v1_go_value(handle, field, BigInt(at)));
}

function frameText(handle) {
  const length = exports.nw_api_v1_render(handle, BigInt(framePtr),
    1048576n, 0n, 912n, 684n);
  assert.ok(length > 0n);
  const bytes = new Uint8Array(exports.memory.buffer, framePtr,
    Number(length)).slice();
  return decode(bytes).filter(command => command.kind === Kind.TEXT)
    .map(command => command.text);
}

function readPublicLastField(handle) {
  const length = exports.nw_api_v1_read_state(handle, BigInt(framePtr), 112n);
  assert.equal(length, 112n);
  return new DataView(exports.memory.buffer).getBigInt64(framePtr + 104, true);
}

try {
  assert.equal(task, 2946453024n);
  assert.ok(exports.nw_api_v1_create(task, 1n, 1n, 2n,
    0n, 0n, 0n, 0n, 17n) < 0n,
  "Go accepts only the source trial-count choices");
  const run = create(1, 1, 17);
  assert.equal(info(run, INFO.phase), 0);
  assert.equal(info(run, INFO.totalTrials), 1);
  assert.ok(frameText(run).includes("Press Space to start — difficulty 1/10"));

  // The source maps 1–9 and 0 to starting levels only while ready or done.
  assert.equal(dispatch(run, EVENT.keyDown, 21), 1n); // 9
  assert.equal(info(run, INFO.difficulty), 9);
  assert.equal(dispatch(run, EVENT.keyDown, 22), 1n); // 0 means 10
  assert.equal(info(run, INFO.difficulty), 10);
  assert.equal(dispatch(run, EVENT.keyDown, 12), 1n); // restore level 1
  assert.equal(info(run, INFO.difficulty), 1);
  assert.equal(dispatch(run, EVENT.action, ACTION.start), 1n);
  assert.equal(info(run, INFO.phase), 1);
  assert.equal(dispatch(run, EVENT.keyDown, 19), 2n,
    "level hotkeys are ignored while solving");

  const size = info(run, INFO.size);
  const winning = info(run, INFO.winning);
  assert.equal(size, 5);
  assert.ok(winning >= 0 && winning < size * size);
  assert.equal(info(run, INFO.best), 1);
  assert.equal(value(run, VALUE_BOARD, winning), 0,
    "the winning intersection starts empty");

  assert.equal(dispatch(run, EVENT.action, ACTION.answer, winning), 1n);
  assert.equal(info(run, INFO.phase), 2);
  assert.equal(info(run, INFO.verdict), 1);
  assert.equal(info(run, INFO.correct), 1);
  assert.equal(info(run, INFO.captured), 1);
  assert.equal(value(run, VALUE_BOARD, winning), 1,
    "the correct move is placed on the board");
  assert.ok(frameText(run).some(text => text === "Winning move — captured 1 stones"));
  assert.equal(readPublicLastField(run), 1n,
    "the public state reports captures, not the winning intersection");

  assert.equal(dispatch(run, EVENT.action, ACTION.next), 1n);
  assert.equal(info(run, INFO.phase), 3);
  assert.equal(info(run, INFO.size), 0);
  assert.equal(info(run, INFO.winning), -1,
    "the source clears the board after the run ends");
  assert.equal(info(run, INFO.correct), 1);
  assert.ok(frameText(run).includes("1 of 1 winning moves found — difficulty 1/10"));

  // A run restarted from DONE resets the score and retains the chosen level.
  assert.equal(dispatch(run, EVENT.action, ACTION.level, 5), 1n);
  assert.equal(info(run, INFO.difficulty), 5);
  assert.equal(dispatch(run, EVENT.action, ACTION.start), 1n);
  assert.equal(info(run, INFO.phase), 1);
  assert.equal(info(run, INFO.trial), 1);
  assert.equal(info(run, INFO.correct), 0);

  const occupied = Array.from({ length: info(run, INFO.size) ** 2 }, (_, cell) => cell)
    .find(cell => value(run, VALUE_BOARD, cell) !== 0);
  assert.notEqual(occupied, undefined);
  assert.equal(dispatch(run, EVENT.action, ACTION.answer, occupied), 1n);
  assert.equal(info(run, INFO.phase), 2);
  assert.equal(info(run, INFO.verdict), 2);
  assert.equal(info(run, INFO.captured), 0);
  assert.ok(frameText(run).includes("That intersection is occupied"));
  assert.equal(exports.nw_api_v1_destroy(run), 0n);

  // Pointer hit testing follows source nearest-intersection rounding, strict
  // 0.42-step tolerance, and top-row indexing despite the bottom-left viewport.
  const pointerRun = create(1, 1, 17);
  assert.equal(dispatch(pointerRun, EVENT.action, ACTION.start), 1n);
  const point = info(pointerRun, INFO.winning);
  const boardLeft = 290;
  const boardBottom = 220.5;
  const step = 83;
  const px = boardLeft + (point % 5) * step;
  const py = boardBottom + (4 - Math.floor(point / 5)) * step;
  const xMill = Math.round(px * 1000000 / 912);
  const yMill = Math.round(py * 1000000 / 684);
  const nearX = Math.round((px + 0.41 * step) * 1000000 / 912);
  assert.equal(dispatch(pointerRun, EVENT.pointerDown, 0, 0, nearX, yMill), 1n);
  assert.equal(info(pointerRun, INFO.phase), 2,
    "a hit within the source tolerance reaches the intended row-major point");
  assert.equal(info(pointerRun, INFO.verdict), 1);
  assert.equal(exports.nw_api_v1_destroy(pointerRun), 0n);

  console.log("go_game_smoke: PASS (source options, hotkeys, run restart, correct and occupied feedback, pointer tolerance/orientation, render, cleanup)");
} finally {
  exports.nw_frame_free?.(BigInt(framePtr));
}
