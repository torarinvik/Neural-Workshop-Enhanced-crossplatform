// Replay the original Go UI and its exact GoEnv port map through common-v1.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const workspaceRoot = fileURLToPath(new URL("../../", import.meta.url));
const oracle = JSON.parse(execFileSync("python3", [
  `${root}/test/go_source_oracle.py`,
], {
  cwd: root,
  encoding: "utf8",
  env: { ...process.env, NW_HEADLESS: "1",
    PYTHONPATH: `${workspaceRoot}/original-neural-workshop-enhanced` },
  maxBuffer: 8 * 1024 * 1024,
}));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });

const task = BigInt(exports.nw_api_v1_task_go_winning_move());
const handle = exports.nw_api_v1_create(task, 1n,
  BigInt(oracle.level), BigInt(oracle.trials), 0n, 0n, 0n, 0n,
  BigInt(oracle.seed));
assert.ok(handle > 0n, "common-v1 should accept source Go options");
const ACTION = Object.freeze({ start: 0n, answer: 1n, next: 2n });
const INFO = Object.freeze({ phase: 0, difficulty: 1, trial: 2,
  totalTrials: 3, size: 4, cursorX: 5, cursorY: 6, correct: 7,
  verdict: 8, best: 9, captureOptions: 10, winning: 11, captured: 12 });
const VALUE = Object.freeze({ board: 0, target: 1 });
let timestamp = 100;
let sequence = 0;

function info(field) {
  return Number(exports.nw_api_v1_go_info(handle, BigInt(field)));
}

function values(field, size) {
  return Array.from({ length: size * size }, (_, cell) =>
    Number(exports.nw_api_v1_go_value(handle, BigInt(field), BigInt(cell))));
}

function action(name, value = 0) {
  return exports.nw_api_v1_dispatch(handle, 1n, BigInt(timestamp++),
    BigInt(sequence++), ACTION[name], BigInt(value), 0n, 0n, 0n, 0n, 0n);
}

function controllerText() {
  const framePtr = Number(exports.nw_frame_alloc(1048576n));
  const length = Number(exports.nw_api_v1_render(handle, BigInt(framePtr),
    1048576n, 0n, 912n, 684n));
  assert.ok(length > 0);
  const bytes = new Uint8Array(exports.memory.buffer, framePtr, length).slice();
  exports.nw_frame_free(BigInt(framePtr));
  return decode(bytes).filter(command => command.kind === Kind.TEXT);
}

function compare(expected, index) {
  const phase = info(INFO.phase);
  const context = `source Go replay index ${index}`;
  for (const field of ["difficulty", "trial", "totalTrials", "size",
    "cursorX", "cursorY", "correct"]) {
    assert.equal(info(INFO[field]), expected[field], `${context}: ${field}`);
  }
  if (expected.verdict === null) {
    assert.equal(info(INFO.verdict), -1, `${context}: no verdict yet`);
  } else {
    assert.equal(info(INFO.verdict) === 1, expected.verdict,
      `${context}: correct/incorrect verdict`);
  }
  assert.equal(phase, expected.phase, `${context}: phase`);
  assert.deepEqual(values(VALUE.board, expected.size), expected.board,
    `${context}: full board`);
  assert.deepEqual(values(VALUE.target, expected.size), expected.target,
    `${context}: target mask`);
  if (expected.winningPort >= 0) {
    assert.equal(info(INFO.winning), expected.winningPort,
      `${context}: diagnostic winning point`);
    assert.equal(info(INFO.best), expected.captureGoal,
      `${context}: winning capture size`);
    assert.equal(info(INFO.captureOptions), expected.captureOptions,
      `${context}: legal capture count`);
  } else {
    assert.equal(info(INFO.winning), -1, `${context}: no stale answer after DONE`);
  }
  if (expected.captured !== undefined) {
    assert.equal(info(INFO.captured), expected.captured,
      `${context}: captured stone count`);
  }
  const text = controllerText();
  const verdicts = text.filter(command => command.color === 0x40ff40ff || command.color === 0xff4040ff);
  if (expected.verdictText === null) {
    assert.equal(verdicts.length, 0, `${context}: no colored verdict before answering`);
  } else {
    assert.equal(verdicts.length, 1, `${context}: one colored verdict`);
    assert.equal(verdicts[0].color, expected.verdict ? 0x40ff40ff : 0xff4040ff, context);
    assert.equal(verdicts[0].text, expected.verdictText, context);
    assert.equal(verdicts[0].b, 60, `${context}: verdict in the bottom band`);
  }
  if (phase === 2 || phase === 3) {
    const displayMessage = phase === 3
      ? `${expected.message} — difficulty ${expected.difficulty}/10`
      : expected.message;
    assert.ok(text.some(command => command.text === displayMessage),
      `${context}: display list should show source feedback ${JSON.stringify(displayMessage)}`);
  }
}

try {
  assert.equal(task, 2946453024n, "Go keeps its stable task ID");
  assert.equal(oracle.trials, 5, "the source default trial choices include five");
  for (const [index, record] of oracle.trace.entries()) {
    const result = action(record.action, record.value);
    assert.equal(result, 1n,
      `source Go ${record.action}(${record.value}) rejected at trace index ${index}`);
    compare(record.state, index);
  }
  assert.equal(info(INFO.correct), 2, "the source run score counts both correct positions");
  assert.equal(info(INFO.phase), 3, "the source UI reaches DONE after all five positions");
  console.log(`go_original_replay_test: PASS (${oracle.trace.length} source UI/environment actions, full boards and targets, occupied/no-capture/decoy/correct feedback, score and DONE)`);
} finally {
  assert.equal(exports.nw_api_v1_destroy(handle), 0n);
}
