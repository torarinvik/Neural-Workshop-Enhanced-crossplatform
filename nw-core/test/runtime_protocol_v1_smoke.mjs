// Contract tests for the common WASM task lifecycle. These intentionally use
// only opaque handles and the task-neutral v1 functions (not legacy pointers).
import assert from "node:assert/strict";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const TASK = Object.freeze({
  monkey: BigInt(exports.nw_api_v1_task_monkey_ladder()),
  sokoban: BigInt(exports.nw_api_v1_task_sokoban()),
  count: BigInt(exports.nw_api_v1_task_count()),
  tetris: BigInt(exports.nw_api_v1_tetris_task_id()),
  marble: 642986n,
});
const STATUS = Object.freeze({
  accepted: 1n, ignored: 2n, invalidHandle: -1n, unsupportedTask: -2n,
  badOptions: -3n, tableFull: -5n, badEvent: -6n, eventOrder: -7n,
  buffer: -8n, unsupported: -9n, time: -10n, version: -11n,
});
const EVENT = Object.freeze({ action: 1, keyDown: 2, text: 8, pointerDown: 5 });
const KEY = Object.freeze({ space: 1, enter: 2, left: 3, up: 4, right: 5,
  down: 6, one: 12, two: 13, three: 14, four: 15, five: 16, six: 17,
  undo: 8, restart: 9 });
const ACTION = Object.freeze({ monkeyStart: 0, monkeyTick: 1,
  monkeySelect: 2, sokobanSpace: 0, marbleStart: 0, marbleRestart: 1,
  marbleReport: 3, marbleBoardReady: 4, marbleNext: 5, marbleScore: 10,
  marbleSyncSettleTime: 11, marbleRecordResult: 12 });
const MARBLE_RESULT = Object.freeze({ rung: 100, elapsedMs: 101,
  home: 102, lost: 103, verdict: 104, scoreWin: 105, boardSeed: 106 });
const STATE = Object.freeze({ bytes: 112, magic: 0x3152574e,
  monkey: { phase: 0, grid: 1, level: 2, roundLevel: 3, length: 4,
    nextIndex: 5, wrong: 6, cursor: 7, cursorEnabled: 8, adaptive: 9,
    reveal: 10, deadline: 11 },
  sokoban: { phase: 0, rung: 1, trial: 2, trials: 3, player: 4,
    pushes: 5, moves: 6, verdict: 7, width: 8, height: 9,
    solved: 10, lost: 11 },
  marble: { phase: 0, rung: 1, trial: 2, trials: 3,
    boardGeneration: 4, seed: 5, elapsed: 6, remaining: 7,
    verdict: 8, wins: 9, losses: 10, heldMask: 11 },
  tetris: { phase: 0, rung: 1, piece: 2, score: 3, selected: 4,
    quarter: 5, column: 6, row: 7, remainder: 8 },
});
// Freeform Tetris renders a deliberately wide 72x32 field and its ordered
// display list can exceed the legacy 64 KiB diagnostic buffer. The production
// web shell already reserves this 1 MiB frame capacity.
const FRAME_BYTES = 1048576;
const STATE_BUFFER = Number(exports.nw_frame_alloc(BigInt(STATE.bytes + 16)));
const FRAME_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
const SNAPSHOT_BUFFER = Number(exports.nw_frame_alloc(BigInt(FRAME_BYTES)));
assert.ok(STATE_BUFFER > 0 && FRAME_BUFFER > 0 && SNAPSHOT_BUFFER > 0);

function create(task, options, seed = 1n, version = 1n) {
  return exports.nw_api_v1_create(task, version, ...options, seed);
}
function state(handle, capacity = BigInt(STATE.bytes), pointer = BigInt(STATE_BUFFER)) {
  const length = exports.nw_api_v1_read_state(handle, pointer, capacity);
  if (length < 0n) return length;
  assert.equal(length, BigInt(STATE.bytes));
  const view = new DataView(instance.exports.memory.buffer, Number(pointer), Number(length));
  assert.equal(view.getUint32(0, true), STATE.magic, "NWR1 state envelope");
  assert.equal(view.getUint32(4, true), 1, "state schema version");
  assert.equal(view.getUint32(12, true), 12, "payload field count");
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}
function event(handle, kind, timestamp, sequence, code, value = 0n,
               flags = 0n, x = 0n, y = 0n) {
  return exports.nw_api_v1_dispatch(...[handle, kind, timestamp, sequence,
    code, value, 0, flags, x, y, 0].map(BigInt));
}
function eventAux(handle, kind, timestamp, sequence, code, value = 0n,
                  aux = 0n, flags = 0n) {
  return exports.nw_api_v1_dispatch(...[handle, kind, timestamp, sequence,
    code, value, 0, flags, 0, 0, aux].map(BigInt));
}
function render(handle, capacity = BigInt(FRAME_BYTES)) {
  const length = exports.nw_api_v1_render(handle, BigInt(FRAME_BUFFER),
    capacity, 0n, 912n, 684n);
  if (length < 0n) return length;
  return new Uint8Array(instance.exports.memory.buffer, FRAME_BUFFER,
    Number(length)).slice();
}

assert.equal(Number(exports.nw_api_v1_abi_version()), 1);
assert.ok(TASK.monkey > 0n && TASK.sokoban > 0n && TASK.count > 0n &&
  TASK.tetris > 0n && TASK.monkey !== TASK.sokoban &&
  TASK.count !== TASK.sokoban && TASK.tetris !== TASK.sokoban);
assert.equal(Number(exports.nw_api_v1_supports(TASK.monkey)), 1);
assert.equal(Number(exports.nw_api_v1_supports(TASK.sokoban)), 1);
assert.equal(Number(exports.nw_api_v1_supports(TASK.count)), 1);
assert.equal(Number(exports.nw_api_v1_supports(TASK.tetris)), 1);
assert.equal(Number(exports.nw_api_v1_supports(TASK.marble)), 1);
assert.equal(create(TASK.marble, [1n, 1n, 2n, 0n, 0n, 0n]), STATUS.badOptions,
  "Marble Maze adaptive option must be boolean");
assert.equal(create(TASK.marble, [1n, 1n, 0n, 0n, 10000n, 0n]), STATUS.badOptions,
  "Marble Maze tray time must use an original option value");
assert.equal(create(TASK.marble, [1n, 1n, 0n, 0n, 15000n, 2n]), STATUS.badOptions,
  "Marble Maze shadow option must be boolean");
assert.equal(create(TASK.monkey, [5n, 3n, 1n, 700n, 280n, 1n], 1n, 2n), STATUS.version);
assert.equal(create(TASK.monkey, [2n, 3n, 1n, 700n, 280n, 1n]), STATUS.badOptions);
assert.equal(create(TASK.sokoban, [2n, 1n, 2n, 0n, 0n, 0n]), STATUS.badOptions);
assert.equal(create(TASK.count, [0n, 8n, 15n, 1n, 1n, 1n]), STATUS.badOptions,
  "Count rejects exposure values outside the source option set");
assert.equal(create(TASK.tetris, [0n, 3n, 5n, 0n, 0n, 0n]), STATUS.badOptions,
  "Tetris rejects a rung below the source range");

// Freeform Tetris now enters the common opaque-handle registry. Its source
// controller owns the hand, rotation, hard drop, score, and restart state;
// this smoke intentionally exercises the common key/event path rather than a
// shell-local preview.
const tetris = create(TASK.tetris, [1n, 3n, 5n, 0n, 0n, 0n], 23n);
assert.deepEqual(state(tetris), [0n, 1n, 0n, 0n, 0n, 0n, 0n, 0n, 3n, 0n, 0n, 0n]);
assert.equal(event(tetris, EVENT.keyDown, 1000n, 0n, KEY.space, 32n), STATUS.accepted);
assert.deepEqual(state(tetris).slice(0, 9), [1n, 1n, 0n, 0n, 0n, 0n, 0n, 0n, 3n]);
assert.equal(event(tetris, EVENT.keyDown, 1001n, 1n, KEY.up, 38n), STATUS.accepted);
assert.equal(state(tetris)[STATE.tetris.quarter], 1n);
assert.equal(event(tetris, EVENT.keyDown, 1002n, 2n, KEY.two, 50n), STATUS.accepted);
assert.equal(state(tetris)[STATE.tetris.selected], 1n,
  "number keys select an offered hand slot rather than advancing a conveyor");
assert.equal(event(tetris, EVENT.keyDown, 1003n, 3n, KEY.down, 40n), STATUS.accepted);
assert.equal(state(tetris)[STATE.tetris.piece], 1n);
assert.equal(state(tetris)[STATE.tetris.remainder], 2n);
const tetrisFrame = render(tetris);
assert.ok(decode(tetrisFrame).some((command) => command.kind === Kind.TEXT &&
  command.text.includes("Freeform Tetris")));
assert.deepEqual(render(tetris), tetrisFrame, "Tetris render is observational");
const tetrisBeforeSnapshot = state(tetris);
const tetrisSnapshotBytes = exports.nw_api_v1_snapshot(
  tetris, BigInt(SNAPSHOT_BUFFER), BigInt(FRAME_BYTES));
assert.ok(tetrisSnapshotBytes > 16n,
  "Tetris fixed-layout controller supports a versioned snapshot");
const tetrisRestored = exports.nw_api_v1_restore(
  BigInt(SNAPSHOT_BUFFER), tetrisSnapshotBytes);
assert.ok(tetrisRestored > tetris, "Tetris restore returns a fresh handle");
assert.deepEqual(state(tetrisRestored), tetrisBeforeSnapshot,
  "restored Tetris state matches the saved hand and board state");
assert.deepEqual(render(tetrisRestored), tetrisFrame,
  "restored Tetris render matches the saved display state");
assert.equal(exports.nw_api_v1_destroy(tetrisRestored), 0n);
assert.equal(exports.nw_api_v1_destroy(tetris), 0n);

const tetrisPointer = create(TASK.tetris, [1n, 3n, 5n, 0n, 0n, 0n], 24n);
assert.equal(event(tetrisPointer, EVENT.keyDown, 1000n, 0n, KEY.space, 32n), STATUS.accepted);
// Logical 912x684 tray geometry: this point is inside hand slot 2.
assert.equal(event(tetrisPointer, EVENT.pointerDown, 1001n, 1n, 0n, 0n, 0n,
  405000n, 756000n), STATUS.accepted,
  "tray pointer selection reaches the controller");
assert.equal(state(tetrisPointer)[STATE.tetris.selected], 1n);
assert.equal(exports.nw_api_v1_destroy(tetrisPointer), 0n);

// Count is a real lifecycle controller, not only the existing stateless
// counting scene: the same common key/text/advance events own the answer.
const count = create(TASK.count, [0n, 8n, 15n, 0n, 1n, 1n], 23n);
assert.deepEqual(state(count), [0n, 0n, 8n, 0n, 15n, 0n, 0n, 0n, 0n, -1n, 1n, 0n]);
assert.equal(event(count, EVENT.keyDown, 1000n, 0n, KEY.space, 32n), STATUS.accepted);
assert.deepEqual(state(count).slice(0, 5), [1n, 0n, 8n, 1n, 15n]);
assert.equal(event(count, EVENT.text, 1001n, 1n, 0n, 56n), STATUS.accepted,
  "ASCII text input reaches Count's numeric answer buffer");
assert.equal(state(count)[6], 8n);
assert.equal(event(count, EVENT.keyDown, 1002n, 2n, KEY.enter, 13n), STATUS.accepted);
assert.deepEqual(state(count).slice(0, 6), [3n, 0n, 9n, 1n, 15n, 1n]);
assert.equal(exports.nw_api_v1_advance(count, 1803n, 0n, 3n), STATUS.accepted);
assert.deepEqual(state(count).slice(0, 6), [1n, 0n, 9n, 2n, 15n, 1n]);
assert.equal(exports.nw_api_v1_destroy(count), 0n);

// Monkey Ladder: options, reveal timing, input-order contract, pointer mapping,
// private answer state, read-only rendering, and bounded-buffer failures.
const monkey = create(TASK.monkey, [5n, 3n, 1n, 700n, 280n, 1n], 1n);
assert.ok(monkey > 0n, "run handle is positive and separate from a linear-memory address");
assert.equal(exports.nw_api_v1_marble_grain_seed(monkey), -2,
  "the Marble-only scalar accessor rejects other live task handles");
assert.deepEqual(state(monkey), [0n, 5n, 3n, 3n, 0n, 0n, -1n, 0n, 0n, 1n, 1n, 0n]);
assert.equal(state(monkey, 111n), STATUS.buffer, "undersized state output fails before writing");
assert.equal(state(monkey, 112n, 0n), STATUS.buffer, "null output pointer is rejected");
assert.equal(state(monkey, 112n, 0xfffffff0n), STATUS.buffer,
  "out-of-linear-memory output range is rejected without trapping");
assert.equal(state(monkey, 112n, BigInt(STATE_BUFFER + 1)), STATUS.buffer,
  "misaligned i64 state output is rejected");
assert.equal(render(monkey, 8n), STATUS.buffer, "undersized render output is reported");

assert.equal(event(monkey, EVENT.action, 100n, 0n, ACTION.monkeySelect, 0n),
  STATUS.ignored, "a selection cannot answer before reveal");
assert.equal(event(monkey, EVENT.action, 100n, 1n, ACTION.monkeyStart), STATUS.accepted);
assert.equal(state(monkey)[STATE.monkey.phase], 1n, "start enters SHOW");
assert.equal(exports.nw_api_v1_advance(monkey, 1639n, 10n, 2n), STATUS.ignored,
  "an early advance does not reveal the sequence");
assert.equal(state(monkey)[STATE.monkey.phase], 1n);
assert.equal(exports.nw_api_v1_advance(monkey, 1640n, 1n, 3n), STATUS.accepted,
  "deadline is inclusive");
assert.equal(state(monkey)[STATE.monkey.phase], 2n, "deadline enters INPUT");

assert.equal(event(monkey, EVENT.pointerDown, 1641n, 4n, 0n, 1n,
  0n, 1000001n, 250000n), STATUS.badEvent,
  "malformed normalized coordinates fail without consuming event order");
assert.equal(event(monkey, EVENT.pointerDown, 1641n, 4n, 0n, 1n,
  0n, 315000n, 240000n), STATUS.accepted,
  "a valid primary pointer event at the same sequence is accepted");
const unchangedMonkeyFrame = render(monkey);
assert.ok(unchangedMonkeyFrame instanceof Uint8Array && unchangedMonkeyFrame.length > 0);
assert.deepEqual(render(monkey), unchangedMonkeyFrame,
  "render is observational and byte-stable for unchanged state");
assert.equal(exports.nw_api_v1_drain_effects(monkey, 0n, 0n), 0n,
  "the conformance controller has no queued host effects");
const monkeyBeforeSnapshot = state(monkey);
const monkeySnapshotBytes = exports.nw_api_v1_snapshot(
  monkey, BigInt(SNAPSHOT_BUFFER), BigInt(FRAME_BYTES));
assert.ok(monkeySnapshotBytes > 16n, "Monkey Ladder snapshot contains a versioned payload");
assert.equal(exports.nw_api_v1_snapshot(monkey, 0n, 0n), STATUS.buffer,
  "snapshot validates output capacity and pointer before copying");
assert.equal(exports.nw_api_v1_restore(BigInt(STATE_BUFFER), 8n), STATUS.buffer,
  "truncated snapshots are rejected before parsing");
const monkeyRestored = exports.nw_api_v1_restore(
  BigInt(SNAPSHOT_BUFFER), monkeySnapshotBytes);
assert.ok(monkeyRestored > monkey, "restore returns a fresh opaque handle");
assert.deepEqual(state(monkeyRestored), monkeyBeforeSnapshot,
  "restored Monkey Ladder state matches the saved controller state");
assert.equal(exports.nw_api_v1_destroy(monkeyRestored), 0n);
assert.equal(event(monkey, EVENT.action, 1642n, 4n, ACTION.monkeySelect, 0n),
  STATUS.eventOrder, "sequence numbers must be strictly increasing");
assert.equal(exports.nw_api_v1_advance(monkey, 1640n, 0n, 5n), STATUS.eventOrder,
  "logical time cannot move backwards");
assert.equal(exports.nw_api_v1_destroy(monkey), 0n);
assert.equal(exports.nw_api_v1_destroy(monkey), 0n, "destroy is idempotent for a retained tombstone");
assert.equal(state(monkey), STATUS.invalidHandle, "destroyed handles cannot be read");
assert.equal(exports.nw_api_v1_marble_grain_seed(monkey), -1,
  "the Marble-only scalar accessor rejects destroyed handles");

// Sokoban: the same event/read/render/destroy lifecycle drives a real generated
// board, not a shell-side answer or a synthetic phase change.
const sokoban = create(TASK.sokoban, [2n, 1n, 0n, 0n, 0n, 0n], 17n);
assert.ok(sokoban > monkey);
assert.deepEqual(state(sokoban), [0n, 2n, 0n, 1n, 0n, 0n, 0n, -1n, 0n, 0n, 0n, 0n]);
assert.equal(event(sokoban, EVENT.keyDown, 1000n, 0n, KEY.space, 32n), STATUS.accepted);
const started = state(sokoban);
assert.equal(started[STATE.sokoban.phase], 1n, "Space starts a generated level");
assert.ok(started[STATE.sokoban.width] > 0n && started[STATE.sokoban.height] > 0n);
const sokobanFrame = render(sokoban);
assert.deepEqual(render(sokoban), sokobanFrame, "Sokoban render is observational");
assert.ok(decode(sokobanFrame).some((command) => command.kind === Kind.TEXT &&
  command.text.includes("Sokoban")));
assert.equal(event(sokoban, EVENT.keyDown, 1001n, 1n, KEY.up, 38n), STATUS.accepted);
assert.equal(event(sokoban, EVENT.keyDown, 1001n, 2n, KEY.undo, 85n), STATUS.accepted);
assert.equal(exports.nw_api_v1_advance(sokoban, 1002n, 1n, 3n), STATUS.accepted);
assert.equal(exports.nw_api_v1_destroy(sokoban), 0n);
assert.equal(exports.nw_api_v1_destroy(sokoban), 0n);

// Marble Maze shares the same authoritative lifecycle. The host continues to
// own the physics engine, but the controller owns phase, elapsed time, board
// identity, held semantic input, adaptive rung, trial count, and verdict.
const marble = create(TASK.marble, [1n, 3n, 1n, 2600n, 0n, 1n], 17n);
assert.ok(marble > sokoban);
assert.deepEqual(state(marble), [0n, 1n, 0n, 3n, 1n, 0n, 0n, 45000n, -1n, 0n, 0n, 0n]);
assert.equal(exports.nw_api_v1_marble_grain_seed(marble), 0,
  "READY does not consume or expose a first-tray grain draw");
assert.equal(event(marble, EVENT.keyDown, 1000n, 0n, KEY.space, 32n), STATUS.accepted,
  "the original Space key starts Marble Maze");
assert.equal(state(marble)[STATE.marble.phase], 1n, "start enters RUNNING");
assert.equal(state(marble)[STATE.marble.trial], 1n,
  "the first trial is dealt only when Space starts the run");
assert.equal(state(marble)[STATE.marble.seed], 889418965n,
  "the first board seed is drawn at the native start boundary");
assert.ok(Math.abs(exports.nw_api_v1_marble_grain_seed(marble) -
  3.2267631084747164) < 1e-15,
  "first-tray grain seed matches the original shared CPython RNG after start");
assert.equal(event(marble, EVENT.keyDown, 1001n, 1n, KEY.right, 39n), STATUS.accepted);
assert.equal(state(marble)[STATE.marble.heldMask], 2n,
  "directional key-down is controller state, not a JS-only hold");
assert.equal(event(marble, 3n, 1002n, 2n, KEY.right, 39n), STATUS.accepted);
assert.equal(state(marble)[STATE.marble.heldMask], 0n,
  "directional key-up clears the controller hold");
assert.equal(exports.nw_api_v1_advance(marble, 2000n, 1000n, 3n), STATUS.accepted);
assert.equal(state(marble)[STATE.marble.elapsed], 1000n);
assert.equal(eventAux(marble, EVENT.action, 2000n, 4n,
  ACTION.marbleReport, 4n, 40000n), STATUS.badEvent,
  "outcome payload validation is explicit and does not consume event order");
assert.equal(eventAux(marble, EVENT.action, 2000n, 4n,
  ACTION.marbleReport, 3n, 40000n), STATUS.accepted);
assert.equal(state(marble)[STATE.marble.phase], 2n, "physics report enters FEEDBACK");
assert.equal(state(marble)[STATE.marble.verdict], 1n);
assert.equal(state(marble)[STATE.marble.rung], 1n,
  "the displayed rung remains the one whose physics result is in feedback");
assert.equal(eventAux(marble, EVENT.action, 2001n, 5n,
  ACTION.marbleReport, 0n, 40000n), STATUS.ignored,
  "a duplicate/stale physics result cannot overwrite feedback");
assert.equal(eventAux(marble, EVENT.action, 2002n, 6n,
  ACTION.marbleRecordResult, 1n, 0n), STATUS.accepted,
  "the host commits the physics-owned counts before feedback can advance");
assert.equal(exports.nw_api_v1_advance(marble, 4599n, 2599n, 7n), STATUS.accepted);
assert.equal(state(marble)[STATE.marble.phase], 2n, "feedback deadline is inclusive");
assert.equal(exports.nw_api_v1_advance(marble, 4600n, 1n, 8n), STATUS.accepted);
const nextMarbleTray = state(marble);
assert.equal(nextMarbleTray[STATE.marble.phase], 3n, "expired feedback requests the next board");
assert.equal(nextMarbleTray[STATE.marble.trial], 2n);
assert.equal(nextMarbleTray[STATE.marble.boardGeneration], 2n);
assert.equal(nextMarbleTray[STATE.marble.seed], 785170443n,
  "next tray seed follows the reference's intervening grain-seed draw");
assert.ok(Math.abs(exports.nw_api_v1_marble_grain_seed(marble) -
  1.158501511057862) < 1e-15,
  "second-tray grain seed matches the original shared CPython RNG");
assert.equal(nextMarbleTray[STATE.marble.rung], 2n);
assert.equal(event(marble, EVENT.action, 4601n, 9n,
  ACTION.marbleBoardReady), STATUS.accepted);
assert.equal(state(marble)[STATE.marble.phase], 1n);
assert.equal(event(marble, EVENT.keyDown, 4602n, 10n, KEY.up, 38n), STATUS.accepted);
assert.equal(event(marble, 9n, 4603n, 11n, 0n, 0n), STATUS.ignored,
  "focus loss is an ordered input-release event");
assert.equal(state(marble)[STATE.marble.heldMask], 0n);
assert.equal(exports.nw_api_v1_advance(marble, 7214n, 9n, 12n), STATUS.accepted);
const elapsedBeforeRestart = state(marble)[STATE.marble.elapsed];
assert.equal(event(marble, EVENT.keyDown, 7215n, 13n, KEY.right, 39n), STATUS.accepted);
assert.equal(state(marble)[STATE.marble.heldMask], 2n);
assert.equal(event(marble, EVENT.keyDown, 7216n, 14n, KEY.restart, 82n), STATUS.accepted,
  "R maps to the controller restart action");
assert.equal(state(marble)[STATE.marble.heldMask], 0n,
  "restart releases directions held on the replaced physics simulation");
assert.ok(elapsedBeforeRestart > 0);
assert.equal(state(marble)[STATE.marble.elapsed], 0n,
  "restart recreates the source Simulation and resets its elapsed clock");
assert.equal(eventAux(marble, EVENT.action, 7217n, 15n,
  ACTION.marbleReport, 0n, 0n), STATUS.accepted);
assert.equal(eventAux(marble, EVENT.action, 7218n, 16n,
  ACTION.marbleRecordResult, 0n, 1n), STATUS.accepted);
assert.equal(state(marble)[STATE.marble.rung], 2n,
  "the in-feedback board keeps its own rung until the transition");
assert.equal(exports.nw_api_v1_advance(marble, 9817n, 2600n, 17n), STATUS.accepted);
assert.equal(state(marble)[STATE.marble.phase], 3n);
assert.equal(event(marble, EVENT.action, 9818n, 18n,
  ACTION.marbleBoardReady), STATUS.accepted);
assert.equal(exports.nw_api_v1_advance(marble, 999999n, 600000n, 19n), STATUS.accepted,
  "the controller clock turns elapsed active time into a timeout result");
assert.equal(state(marble)[STATE.marble.phase], 2n);
assert.equal(state(marble)[STATE.marble.verdict], 0n);
assert.equal(event(marble, EVENT.action, 1000000n, 20n,
  ACTION.marbleScore, 0n), STATUS.accepted,
  "a timeout with a lost marble commits a scored loss");
assert.equal(eventAux(marble, EVENT.action, 1000001n, 21n,
  ACTION.marbleRecordResult, 0n, 1n), STATUS.accepted);
assert.equal(exports.nw_api_v1_advance(marble, 1002599n, 2600n, 22n), STATUS.accepted);
const marbleDone = state(marble);
assert.equal(marbleDone[STATE.marble.phase], 4n, "final feedback enters DONE");
assert.equal(marbleDone[STATE.marble.trial], 3n);
assert.equal(marbleDone[STATE.marble.wins], 1n);
assert.equal(marbleDone[STATE.marble.losses], 2n);
assert.equal(event(marble, EVENT.action, 1002600n, 23n,
  ACTION.marbleStart), STATUS.accepted, "Space starts a new run after the summary");
const freshMarbleRun = state(marble);
assert.equal(freshMarbleRun[STATE.marble.phase], 3n);
assert.equal(freshMarbleRun[STATE.marble.trial], 1n);
assert.equal(freshMarbleRun[STATE.marble.elapsed], 0n,
  "Space from DONE starts a fresh active clock before board preparation");
assert.equal(freshMarbleRun[STATE.marble.boardGeneration], 4n);
assert.equal(freshMarbleRun[STATE.marble.seed], 57846291n,
  "a replay continues the reference stream including every grain draw");
assert.ok(Math.abs(exports.nw_api_v1_marble_grain_seed(marble) -
  0.9956124241403073) < 1e-15,
  "replay exposes its reference-derived wood-grain seed");
assert.equal(exports.nw_api_v1_render(marble, BigInt(FRAME_BUFFER), BigInt(FRAME_BYTES),
  0n, 912n, 684n), STATUS.unsupported,
  "Marble's host physics renderer is explicitly outside the WASM display-list adapter");
assert.equal(exports.nw_api_v1_destroy(marble), 0n);
assert.equal(exports.nw_api_v1_destroy(marble), 0n);

const marbleTimeOverride = create(TASK.marble,
  [4n, 1n, 0n, 2600n, 15000n, 0n], 41n);
assert.equal(state(marbleTimeOverride)[STATE.marble.remaining], 15000n,
  "the task-specific seconds option replaces the generated rung budget");
assert.equal(event(marbleTimeOverride, EVENT.action, 1000n, 0n,
  ACTION.marbleStart), STATUS.accepted);
assert.equal(exports.nw_api_v1_advance(marbleTimeOverride, 16000n, 15000n, 1n), STATUS.accepted);
assert.equal(state(marbleTimeOverride)[STATE.marble.phase], 2n,
  "the configured tray-time boundary produces ordinary timeout feedback");
assert.equal(state(marbleTimeOverride)[STATE.marble.elapsed], 15000n);
assert.equal(state(marbleTimeOverride)[STATE.marble.verdict], 0n);
assert.equal(state(marbleTimeOverride)[STATE.marble.wins], 0n,
  "a timeout waits for the host-owned lost count before source scoring");
assert.equal(event(marbleTimeOverride, EVENT.action, 16001n, 2n,
  ACTION.marbleScore, 1n), STATUS.accepted,
  "the host can commit the source zero-lost score after timeout");
assert.equal(state(marbleTimeOverride)[STATE.marble.wins], 1n,
  "a timed-out tray with no lost marble retains the source score quirk");
assert.equal(exports.nw_api_v1_marble_info(marbleTimeOverride, 12n), 0n,
  "a physics result is not retained until the host supplies its counts");
assert.equal(eventAux(marbleTimeOverride, EVENT.action, 16002n, 3n,
  ACTION.marbleRecordResult, 3n, 0n), STATUS.accepted,
  "the host commits the source result tuple after scoring");
assert.equal(exports.nw_api_v1_marble_info(marbleTimeOverride, 12n), 1n);
assert.equal(exports.nw_api_v1_marble_value(marbleTimeOverride,
  BigInt(MARBLE_RESULT.rung), 0n), 4n);
assert.equal(exports.nw_api_v1_marble_value(marbleTimeOverride,
  BigInt(MARBLE_RESULT.elapsedMs), 0n), 15000n);
assert.equal(exports.nw_api_v1_marble_value(marbleTimeOverride,
  BigInt(MARBLE_RESULT.home), 0n), 3n);
assert.equal(exports.nw_api_v1_marble_value(marbleTimeOverride,
  BigInt(MARBLE_RESULT.lost), 0n), 0n);
assert.equal(exports.nw_api_v1_marble_value(marbleTimeOverride,
  BigInt(MARBLE_RESULT.verdict), 0n), 0n);
assert.equal(exports.nw_api_v1_marble_value(marbleTimeOverride,
  BigInt(MARBLE_RESULT.scoreWin), 0n), 1n);
assert.equal(exports.nw_api_v1_marble_value(marbleTimeOverride,
  BigInt(MARBLE_RESULT.boardSeed), 0n), 818235696n,
  "the retained row keeps the dealt board identity");
assert.equal(eventAux(marbleTimeOverride, EVENT.action, 16003n, 4n,
  ACTION.marbleRecordResult, 3n, 0n), STATUS.ignored,
  "a result row cannot be committed twice");

// A timeout's physical simulation may include the final capped frame beyond
// the configured budget. The host can synchronize that measured source clock
// after the controller enters feedback but before SCORE freezes the row.
const marbleLateTimeout = create(TASK.marble,
  [1n, 1n, 0n, 2600n, 15000n, 0n], 41n);
assert.equal(event(marbleLateTimeout, EVENT.action, 1000n, 0n,
  ACTION.marbleStart), STATUS.accepted);
assert.equal(exports.nw_api_v1_advance(marbleLateTimeout, 16000n, 15000n, 1n),
  STATUS.accepted);
assert.equal(event(marbleLateTimeout, EVENT.action, 16001n, 2n,
  ACTION.marbleSyncSettleTime, 15017n), STATUS.accepted,
  "timeout settle time accepts the source's final-frame overshoot");
assert.equal(event(marbleLateTimeout, EVENT.action, 16002n, 3n,
  ACTION.marbleScore, 1n), STATUS.accepted);
assert.equal(eventAux(marbleLateTimeout, EVENT.action, 16003n, 4n,
  ACTION.marbleRecordResult, 3n, 0n), STATUS.accepted);
assert.equal(exports.nw_api_v1_marble_value(marbleLateTimeout,
  BigInt(MARBLE_RESULT.elapsedMs), 0n), 15017n);
assert.equal(exports.nw_api_v1_destroy(marbleLateTimeout), 0n);

// Native options apply resets the visible run on the same MarbleMaze object,
// so the persistent RNG must continue at the next board rather than replaying
// the first seed from a newly allocated controller.
const marbleApplyOptions = create(TASK.marble,
  [1n, 3n, 1n, 2600n, 0n, 0n], 17n);
assert.equal(event(marbleApplyOptions, EVENT.action, 1000n, 0n,
  ACTION.marbleStart), STATUS.accepted);
assert.equal(state(marbleApplyOptions)[STATE.marble.seed], 889418965n);
assert.equal(exports.nw_api_v1_marble_apply_options(
  marbleApplyOptions, 2n, 8n, 0n, 0n), STATUS.accepted,
  "Marble options apply resets the controller without replacing its RNG");
const optionsReady = state(marbleApplyOptions);
assert.equal(optionsReady[STATE.marble.phase], 0n);
assert.equal(optionsReady[STATE.marble.rung], 2n);
assert.equal(optionsReady[STATE.marble.trial], 0n);
assert.equal(optionsReady[STATE.marble.trials], 8n);
assert.equal(optionsReady[STATE.marble.seed], 0n);
assert.equal(exports.nw_api_v1_marble_grain_seed(marbleApplyOptions), 0,
  "options apply returns Marble to an undealt READY state");
assert.equal(exports.nw_api_v1_marble_apply_options(
  marbleApplyOptions, 17n, 8n, 0n, 0n), STATUS.badOptions,
  "Marble options apply rejects an invalid rung without mutating the run");
assert.equal(event(marbleApplyOptions, EVENT.action, 1001n, 1n,
  ACTION.marbleStart), STATUS.accepted);
assert.equal(state(marbleApplyOptions)[STATE.marble.seed], 785170443n,
  "options apply preserves the next source RNG board seed");
assert.ok(Math.abs(exports.nw_api_v1_marble_grain_seed(marbleApplyOptions) -
  1.158501511057862) < 1e-15,
  "options apply preserves the next source RNG grain seed");
assert.equal(exports.nw_api_v1_destroy(marbleApplyOptions), 0n);

// A physics settle is measured after the final simulation bite. The host may
// synchronize that source elapsed time before REPORT without changing the
// stable state envelope or allowing the clock to move backwards.
const marbleSettleClock = create(TASK.marble, [1n, 1n, 0n, 2600n, 0n, 0n], 17n);
assert.equal(event(marbleSettleClock, EVENT.action, 1000n, 0n,
  ACTION.marbleStart), STATUS.accepted);
assert.equal(exports.nw_api_v1_advance(marbleSettleClock, 2000n, 1000n, 1n), STATUS.accepted);
assert.equal(eventAux(marbleSettleClock, EVENT.action, 2001n, 2n,
  ACTION.marbleSyncSettleTime, 1250n, 1n), STATUS.badEvent,
  "settle-time synchronization validates its auxiliary field");
assert.equal(event(marbleSettleClock, EVENT.action, 2001n, 2n,
  ACTION.marbleSyncSettleTime, 1250n), STATUS.accepted);
assert.equal(state(marbleSettleClock)[STATE.marble.elapsed], 1250n);
assert.equal(eventAux(marbleSettleClock, EVENT.action, 2002n, 3n,
  ACTION.marbleReport, 3n, 40000n), STATUS.accepted);
assert.equal(state(marbleSettleClock)[STATE.marble.phase], 2n);
assert.equal(state(marbleSettleClock)[STATE.marble.wins], 1n);
assert.equal(exports.nw_api_v1_destroy(marbleSettleClock), 0n);

// Source key semantics: Space may leave a completed-tray feedback screen,
// while Enter is not a Marble Maze shortcut in the native UI.
const marbleSpaceAdvance = create(TASK.marble, [1n, 2n, 0n, 2600n, 0n, 0n], 17n);
assert.equal(event(marbleSpaceAdvance, EVENT.keyDown, 1000n, 0n,
  KEY.space, 32n), STATUS.accepted);
assert.equal(eventAux(marbleSpaceAdvance, EVENT.action, 1001n, 1n,
  ACTION.marbleReport, 0n, 0n), STATUS.accepted);
assert.equal(eventAux(marbleSpaceAdvance, EVENT.action, 1002n, 2n,
  ACTION.marbleRecordResult, 0n, 1n), STATUS.accepted);
assert.equal(state(marbleSpaceAdvance)[STATE.marble.phase], 2n);
assert.equal(event(marbleSpaceAdvance, EVENT.keyDown, 1003n, 3n,
  KEY.enter, 13n), STATUS.ignored,
  "Enter does not skip the source's tray feedback interval");
assert.equal(state(marbleSpaceAdvance)[STATE.marble.trial], 1n);
assert.equal(event(marbleSpaceAdvance, EVENT.keyDown, 1004n, 4n,
  KEY.space, 32n), STATUS.accepted,
  "Space retains the source's immediate next-tray behavior");
assert.equal(state(marbleSpaceAdvance)[STATE.marble.phase], 3n);
assert.equal(state(marbleSpaceAdvance)[STATE.marble.trial], 2n);
assert.equal(state(marbleSpaceAdvance)[STATE.marble.seed], 785170443n);
assert.equal(exports.nw_api_v1_destroy(marbleSpaceAdvance), 0n);

// A host that stalls after REPORT must not allow the controller's feedback
// timer to skip an uncommitted source result row. Once the physics-owned
// counts arrive, a zero-delta advance is sufficient to release the already
// expired feedback boundary.
const marbleResultBarrier = create(TASK.marble,
  [1n, 2n, 0n, 2600n, 15000n, 0n], 41n);
assert.equal(event(marbleResultBarrier, EVENT.action, 1000n, 0n,
  ACTION.marbleStart), STATUS.accepted);
assert.equal(eventAux(marbleResultBarrier, EVENT.action, 1001n, 1n,
  ACTION.marbleReport, 0n, 0n), STATUS.accepted);
assert.equal(exports.nw_api_v1_advance(marbleResultBarrier, 3601n, 2600n, 2n),
  STATUS.accepted);
assert.equal(state(marbleResultBarrier)[STATE.marble.phase], 2n,
  "feedback remains visible while the source result row is missing");
assert.equal(event(marbleResultBarrier, EVENT.action, 3602n, 3n,
  ACTION.marbleNext), STATUS.ignored,
  "Space-next cannot discard an uncommitted result row");
assert.equal(eventAux(marbleResultBarrier, EVENT.action, 3603n, 4n,
  ACTION.marbleRecordResult, 0n, 1n), STATUS.accepted);
assert.equal(exports.nw_api_v1_advance(marbleResultBarrier, 3604n, 0n, 5n),
  STATUS.accepted);
assert.equal(state(marbleResultBarrier)[STATE.marble.phase], 3n,
  "the expired feedback boundary advances after the row is committed");
assert.equal(exports.nw_api_v1_destroy(marbleResultBarrier), 0n);
assert.equal(exports.nw_api_v1_destroy(marbleTimeOverride), 0n);

// Every source-supported tray-count option must preserve the same immediate
// Space-next lifecycle, not only the historical three-tray fixture above.
// Report synthetic losses here so the test isolates trial accounting and does
// not make a claim about physics; the browser MuJoCo acceptance run covers the
// host-owned physical path separately.
for (const totalTrials of [1n, 2n, 3n, 5n, 8n, 10n]) {
  const run = create(TASK.marble, [1n, totalTrials, 0n, 2600n, 0n, 0n], 17n);
  let timestamp = 1000n;
  let sequence = 0n;
  assert.equal(event(run, EVENT.action, timestamp++, sequence++, ACTION.marbleStart),
    STATUS.accepted);
  for (let trial = 1n; trial <= totalTrials; trial++) {
    assert.equal(eventAux(run, EVENT.action, timestamp++, sequence++,
      ACTION.marbleReport, 0n, 0n), STATUS.accepted,
      `trial ${trial}/${totalTrials} report is accepted`);
    assert.equal(eventAux(run, EVENT.action, timestamp++, sequence++,
      ACTION.marbleRecordResult, 0n, 1n), STATUS.accepted,
      `trial ${trial}/${totalTrials} result row is committed`);
    const current = state(run);
    assert.equal(current[STATE.marble.trial], trial);
    assert.equal(current[STATE.marble.losses], trial);
    if (trial < totalTrials) {
      assert.equal(event(run, EVENT.action, timestamp++, sequence++,
        ACTION.marbleNext), STATUS.accepted,
        `trial ${trial}/${totalTrials} Space-next is accepted`);
      assert.equal(state(run)[STATE.marble.phase], 3n);
      assert.equal(event(run, EVENT.action, timestamp++, sequence++,
        ACTION.marbleBoardReady), STATUS.accepted);
      assert.equal(state(run)[STATE.marble.phase], 1n);
    } else {
      assert.equal(event(run, EVENT.action, timestamp++, sequence++,
        ACTION.marbleNext), STATUS.accepted,
        `${totalTrials}-tray run reaches DONE through the source next action`);
    }
  }
  const done = state(run);
  assert.equal(done[STATE.marble.phase], 4n);
  assert.equal(done[STATE.marble.trial], totalTrials);
  assert.equal(done[STATE.marble.trials], totalTrials);
  assert.equal(done[STATE.marble.wins], 0n);
  assert.equal(done[STATE.marble.losses], totalTrials);
  assert.equal(exports.nw_api_v1_destroy(run), 0n);
}

// Reuse all registry slots at once, check the hard concurrency bound, then
// prove a stale handle stays invalid when its former slot receives a new run.
const handles = [];
for (let index = 0; index < 64; index++) {
  const handle = create(TASK.monkey, [3n, 2n, 0n, 0n, 0n, 0n], BigInt(index + 1));
  assert.ok(handle > 0n);
  handles.push(handle);
}
assert.equal(create(TASK.monkey, [3n, 2n, 0n, 0n, 0n, 0n]), STATUS.tableFull);
for (const handle of handles) assert.equal(exports.nw_api_v1_destroy(handle), 0n);
const replacement = create(TASK.monkey, [3n, 2n, 0n, 0n, 0n, 0n], 88n);
assert.ok(replacement > handles.at(-1));
assert.equal(state(handles[0]), STATUS.invalidHandle,
  "a stale handle is rejected after its tombstone slot is reused");
assert.equal(exports.nw_api_v1_destroy(replacement), 0n);

console.log("PASS: common WASM runtime API v1 handles, options, events, state, frames, errors, and cleanup");
