import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createMissingWordEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_missing_word();
assert.equal(task, 2323823752n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => api.nw_api_v1_missing_word_info(handle, BigInt(field));
let sequence = 0n;
let now = 0n;
function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function commands(run = handle) {
  return decode(view(api.nw_api_v1_render(run, pointer, capacity, 1n, 912n, 684n)));
}
function dispatch(kind, code, x = 0, y = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, 0n,
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
}
function tick(dt) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}
function click(x, y) {
  assert.equal(dispatch(5, 0, x, y), 1n);
  assert.equal(dispatch(6, 0, x, y), 1n);
}

try {
  assert.equal(TASK_IDS_BY_CATEGORY[4][23], "missing_word");
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 4n, 23n, 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "The Missing Word"));
  assert.equal(new TextDecoder().decode(view(api.nw_missing_word_options_note(pointer, capacity, 4n))),
    "Rung 4: 2 sentence(s), 2 mistake(s) to mend.");
  assert.ok(commands().some(command => command.text === "Press Space or click to start"));
  click(456, 342);
  const words = commands();
  const read = words.find(command => command.text === "read");
  const book = words.find(command => command.text === "book");
  click((read.a + book.a) / 2, read.b - 30 * (389 / 640));
  assert.ok(commands().some(command => command.text === "Put in:"));
  const offered = commands().find(command => command.text === "the");
  click(offered.a, offered.b);
  assert.ok(commands().some(command => command.text === "the" && command.b === read.b));
  assert.ok(view(api.nw_missing_word_audio_window(handle, 0, 0.1, pointer, capacity)).some(byte => byte !== 0));
  assert.equal(dispatch(2, 2), 1n);
  assert.equal(tick(25), 1n);
  assert.equal(info(0), 2n);
  assert.equal(info(1), 2n);
  assert.equal(info(4), 1n);
  assert.equal(info(5), 1n);
  assert.ok(commands().some(command => command.text === "Mended"));
  assert.equal(tick(3999), 2n);
  assert.equal(tick(1), 1n);
  assert.equal(info(0), 3n);
  assert.equal(api.nw_missing_word_options_apply(handle, 4n, 3n, 0n), 1n);
  assert.equal(dispatch(2, 1), 2n);
  assert.equal(info(10), 1n);
  assert.ok(commands().some(command => command.text === "No passage available for this rung"));
  assert.equal(api.nw_missing_word_options_apply(handle, 1n, 1n, 0n), 1n);
  assert.equal(dispatch(2, 1), 1n);
  const rowY = 179 + 540 * (389 / 640);
  const displayedWords = () => commands().filter(command =>
    command.color === 0x282430ff && command.text && Math.abs(command.b - rowY) < 0.001).length;
  const originalCount = displayedWords();
  for (let i = 0; i < 40; i++) {
    const caret = commands().find(command => command.color === 0x786e64ff);
    click(caret.a + 6 * (389 / 640), caret.b + 4 * (389 / 640));
    const choice = commands().find(command => command.text && Math.abs(command.b - (179 + 112 * (389 / 640))) < 0.001);
    assert.ok(choice, `insertion ${i + 1}`);
    click(choice.a, choice.b);
  }
  assert.equal(displayedWords(), originalCount + 40);
  assert.ok(view(api.nw_missing_word_audio_window(handle, 0, 0.1, pointer, capacity)).some(byte => byte !== 0));
  assert.equal(dispatch(2, 9), 1n);
  assert.equal(displayedWords(), originalCount);
  assert.ok(commands().some(command => command.text === "RESET"));
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
}

const cached = api.nw_api_v1_create(task, 1n, 4n, 1n, 0n, 0n, 0n, 0n, 17n);
assert.ok(cached > 0n);
const passage = new TextEncoder().encode("Ada built a wooden boat. Clara painted it bright red.\n".repeat(100));
const source = api.nw_frame_alloc(BigInt(passage.length));
assert.ok(source > 0n);
try {
  new Uint8Array(api.memory.buffer, Number(source), passage.length).set(passage);
  assert.equal(api.nw_missing_word_load(cached, source, BigInt(passage.length), 0n, 0n, 0n, 0n), 1n);
} finally {
  api.nw_frame_free(source);
}
try {
  assert.equal(api.nw_api_v1_dispatch(cached, 2n, 0n, 0n, 1n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
  assert.ok(commands(cached).some(command => command.text === "Ada"));
} finally {
  api.nw_frame_free(pointer);
  assert.equal(api.nw_api_v1_destroy(cached), 0n);
}

const canvas = { width: 228, height: 171 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, moveTo() {}, lineTo() {}, closePath() {},
  clearRect() {}, fillRect() {}, fillText() {},
  getImageData: () => ({ data: pixels }),
};
const env = createMissingWordEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(env.n_actions, 16);
  assert.ok(env.act(2).ok);
  assert.equal(env.advance().done, false);
} finally {
  env.close();
}
const importedEnv = createMissingWordEnvironment(context, {
  seed: 17, rung: 4, trials: 1, frameHz: 20, passageCaches: { passages: passage },
});
try {
  assert.ok(importedEnv.act(2).ok);
  assert.equal(importedEnv.advance().done, false);
} finally {
  importedEnv.close();
}
console.log("PASS: The Missing Word WASM menu, cache import, pointer repairs, adaptive feedback, audio, and agent");
