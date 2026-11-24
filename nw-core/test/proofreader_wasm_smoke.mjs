import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { attachPassageCaches } from "../shells/web/rung-env.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createProofreaderEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_proofreader();
assert.equal(task, 2105479234n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(TASK_IDS_BY_CATEGORY[4][24], "proofreader");
const handle = api.nw_api_v1_create(task, 1n, 4n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => api.nw_api_v1_proofreader_info(handle, BigInt(field));
let sequence = 0n;
let now = 0n;
function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function frame() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)));
}
function dispatch(kind, code = 0, x = 0, y = 0) {
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
const passage = new TextEncoder().encode("Ada built a wooden boat. Clara painted it bright red.\n".repeat(100));
const scale = 389 / 640;
const yAt = y => 179 + scale * y;
const xAt = x => (912 - 1000 * scale) / 2 + scale * x;
const wordsAt = (commands, y) => commands.filter(command => command.color === 0x282430ff &&
  command.text && Math.abs(command.b - yAt(y)) < 0.001);

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 4n, 24n, 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "The Proofreader"));
  assert.equal(new TextDecoder().decode(view(api.nw_proofreader_options_note(pointer, capacity, 4n))),
    "Rung 4: 2 sentence(s), 2 mistake(s) to mend.");
  assert.ok(frame().some(command => command.text === "Press Space or click to start"));
  attachPassageCaches(api, api.nw_proofreader_load, handle, [
    passage,
    new Uint8Array(), new Uint8Array(),
  ]);
  click(456, 342);
  assert.equal(info(0), 1n);
  const dealt = frame();
  assert.equal(wordsAt(dealt, 540)[0].text, "Clara");
  const dragX = xAt(54);
  assert.equal(dispatch(5, 0, dragX, yAt(462)), 1n);
  assert.equal(dispatch(4, 0, dragX, yAt(540)), 1n);
  assert.equal(dispatch(11), 1n);
  // Releasing a cancelled row drag does not reorder the passage.
  assert.equal(dispatch(6, 0, dragX, yAt(540)), 1n);
  assert.equal(info(12), 0n);
  assert.equal(wordsAt(frame(), 540)[0].text, "Clara");
  assert.equal(dispatch(5, 0, dragX, yAt(462)), 1n);
  assert.equal(dispatch(4, 0, dragX, yAt(540)), 1n);
  assert.equal(dispatch(6, 0, dragX, yAt(540)), 1n);
  assert.equal(info(12), 1n);
  assert.equal(wordsAt(frame(), 540)[0].text, "Ada");

  const word = wordsAt(frame(), 540)[1];
  for (let i = 0; i < 80; i++) {
    click(word.a, word.b);
    assert.ok(frame().some(command => command.text === "Its forms:"));
  }
  const option = wordsAt(frame(), 112)[0];
  click(option.a, option.b);
  assert.equal(info(12), 2n);
  assert.ok(view(api.nw_proofreader_audio_window(handle, 0, 0.1, pointer, capacity)).some(byte => byte !== 0));
  assert.equal(dispatch(2, 9), 1n);
  assert.equal(wordsAt(frame(), 540)[0].text, "Clara");
  assert.equal(dispatch(2, 2), 1n);
  assert.equal(tick(25), 1n);
  assert.equal(info(0), 2n);
  assert.equal(info(1), 3n);
  assert.ok(frame().some(command => command.text?.includes("Not as it was written: Ada built a wooden boat.")));
  assert.equal(tick(4000), 1n);
  assert.equal(info(0), 3n);
  assert.equal(api.nw_proofreader_options_apply(handle, 1n, 3n, 0n), 1n);
  assert.equal(info(0), 0n);
  assert.equal(info(3), 3n);
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
const environment = createProofreaderEnvironment(context, {
  seed: 17, rung: 4, trials: 1, frameHz: 20, passageCaches: { passages: passage },
});
try {
  assert.equal(environment.n_actions, 16);
  assert.ok(environment.act(14).ok);
  assert.equal(environment.advance().done, false);
  assert.equal(environment.advance().done, true);
} finally {
  environment.close();
}
console.log("PASS: Proofreader hub, cached passages, row dragging, focus cancellation, word forms, audio, feedback, options and agent");
