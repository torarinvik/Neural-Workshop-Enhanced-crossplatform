import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createMorningRoundEnvironment } = await instantiateElisa(bytes, { warn: false });
const task = api.nw_api_v1_task_morning_round();
assert.equal(task, 806220648n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => api.nw_api_v1_morning_round_info(handle, BigInt(field));
let sequence = 0n;
let now = 0n;
function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function labels() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)))
    .map(command => command.text).filter(text => text !== undefined);
}
function dispatch(kind, code, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n,
    0n, BigInt(flags), 500000n, 500000n, 0n);
}
function tick(dt) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}

try {
  assert.equal(TASK_IDS_BY_CATEGORY[6][4], "morning_round");
  assert.ok(decode(view(api.nw_taskhub_write(pointer, capacity, 6n, 4n, 0n, 912n, 684n)))
    .some(command => command.text === "Morning Round"));
  assert.equal(new TextDecoder().decode(view(api.nw_morning_round_options_note(pointer, capacity, 1n))),
    "Rung 1: 1 rule(s), 1 block(s), 2 mistake(s) allowed.");
  assert.ok(labels().includes("Press Space or click to start"));
  assert.equal(dispatch(5, 2), 2n);
  assert.equal(dispatch(5, 0), 1n);
  assert.ok(labels().includes("Setting off in 2"));
  assert.equal(dispatch(2, 81), 2n);
  for (let i = 0; i < 100; i++) assert.equal(tick(25), 1n);
  const papers = info(13);
  assert.equal(dispatch(2, 81), 1n);
  assert.equal(info(13), papers - 1n);
  const t = Number(info(9)) / 1000;
  const pcm = view(api.nw_morning_round_audio_window(handle, t, t + 0.1, pointer, capacity));
  assert.equal(pcm.length, 8820);
  assert.ok(pcm.some(byte => byte !== 0));
  assert.equal(dispatch(2, 3), 1n);
  assert.equal(dispatch(2, 79), 1n);
  assert.equal(dispatch(3, 3), 1n);
  const x = info(11);
  tick(25);
  assert.ok(info(11) < x);
  assert.equal(dispatch(9, 0), 1n);
  const afterBlur = info(11);
  tick(25);
  assert.equal(info(11), afterBlur);
  for (let i = 0; i < 4; i++) tick(100);
  assert.equal(dispatch(2, 82, 1), 2n);
  assert.equal(info(13), papers - 1n);
  assert.equal(dispatch(2, 82), 1n);
  assert.equal(info(13), papers - 2n);
  while (info(0) === 1n && now < 60000n) tick(100);
  assert.equal(info(0), 2n);
  assert.equal(tick(3499), 2n);
  assert.equal(tick(1), 1n);
  assert.equal(info(0), 3n);
  assert.equal(api.nw_morning_round_options_apply(handle, 13n, 3n, 0n), 1n);
  assert.equal(dispatch(2, 1), 1n);
  assert.equal(info(1), 13n);
  assert.equal(info(3), 3n);
  assert.ok(labels().includes("RULEBOOK"));
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  api.nw_frame_free(pointer);
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
const env = createMorningRoundEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(env.n_actions, 6);
  assert.ok(env.act(2).ok);
  assert.equal(env.advance().done, false);
} finally {
  env.close();
}
console.log("PASS: Morning Round WASM controls, live PCM, settings, and session lifecycle");
