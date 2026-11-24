import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { attachPassageCaches } from "../shells/web/rung-env.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createSocialSenseEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_social_sense();
assert.equal(task, 2281393555n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.deepEqual(TASK_IDS_BY_CATEGORY[10], ["between_the_lines", "social_sense"]);

// The answers are shuffled; the right one is always "Right option".
const cache = new TextEncoder().encode([["social:feel", "The first imported question."],
  ["social:describe", "The second imported question."]]
  .map(([kind, prompt], index) => JSON.stringify({ kind, prompt, ask: "How would they feel?",
    options: index ? ["Wrong option", "Other option", "Right option"] : ["Right option", "Wrong option", "Other option"],
    answer: index ? 2 : 0 })).join("\n"));
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => api.nw_api_v1_social_sense_info(handle, BigInt(field));
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
  assert.ok(api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++) > 0n);
}
function click(text) {
  const label = frame().find(command => command.text === text);
  assert.ok(label, text);
  assert.equal(dispatch(5, 0, label.a, label.b), 1n);
  assert.equal(dispatch(6, 0, label.a, label.b), 1n);
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 10n, 0n, 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Between the Lines"));
  assert.ok(menu.some(command => command.text === "Social Sense"));
  assert.ok(menu.some(command => command.text === "Social") && menu.some(command => command.text === "Rationality"));
  assert.equal(new TextDecoder().decode(view(api.nw_social_sense_options_note(pointer, capacity, 1n))),
    "Rung 1: feel, describe.");
  assert.equal(new TextDecoder().decode(view(api.nw_social_sense_options_note(pointer, capacity, 13n))),
    "Rung 13: feel, describe, want, need, why, others_feel, happens, next.  Two questions a situation.");
  assert.ok(api.nw_social_sense_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(frame().some(command => command.text === "Press Space or click to start"));
  attachPassageCaches(api, api.nw_social_sense_load, handle, [cache]);
  assert.equal(dispatch(2, 1), 1n);
  assert.ok(frame().some(command => command.text?.includes("imported question")));
  for (let item = 0; item < 12; item++) {
    if (item === 0) {
      click("Wrong option");
      assert.ok(frame().some(command => command.text === "No: Right option"));
      assert.ok(view(api.nw_social_sense_audio_window(handle, 0, 0.1, pointer, capacity)).some(byte => byte !== 0));
    } else {
      click("Right option");
      assert.ok(frame().some(command => command.text === "Right: Right option"));
    }
    for (let i = 0; i < 29 && info(0) === 1n && info(10) === BigInt(item); i++) tick(50);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(1), 2n);
  assert.equal(info(4), 1n);
  assert.equal(info(11), 11n);
  tick(2500);
  assert.equal(info(0), 3n);
  assert.ok(frame().some(command => command.text === "1 of 1 passed   highest rung passed 1"));
  assert.equal(api.nw_social_sense_options_apply(handle, 4n, 3n, 0n), 1n);
  assert.equal(info(3), 3n);
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  api.nw_frame_free(pointer);
}

const canvas = { width: 228, height: 171 };
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, moveTo() {}, lineTo() {}, closePath() {},
  clearRect() {}, fillRect() {}, fillText() {},
  getImageData: () => ({ data: new Uint8ClampedArray(canvas.width * canvas.height * 4) }),
};
const environment = createSocialSenseEnvironment(context, {
  seed: 17, rung: 1, trials: 1, frameHz: 20, questionCache: cache,
});
try {
  assert.equal(environment.n_actions, 8);
  assert.ok(environment.act(0).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
const largeCache = new TextEncoder().encode(Array.from({ length: 200 }, (_, index) =>
  JSON.stringify({ kind: index % 2 ? "social:feel" : "social:why", prompt: `Question ${index >> 1}`, ask: `Ask ${index % 2}`,
    options: ["yes", "no", "maybe"], answer: index % 3 })).join("\n"));
const memorySizes = [];
for (let index = 0; index < 20; index++) {
  const replay = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 17n);
  try {
    attachPassageCaches(api, api.nw_social_sense_load, replay, [largeCache]);
    assert.equal(api.nw_social_sense_agent_event(replay, 0, 8n), 1n);
  } finally {
    assert.equal(api.nw_api_v1_destroy(replay), 0n);
  }
  memorySizes.push(api.memory.buffer.byteLength);
}
assert.equal(memorySizes[1], memorySizes.at(-1), "question cache memory should be reclaimed");
console.log("PASS: Social Sense WASM Social tab, saved questions, keys, clicks, round feedback, audio, agent controls and cache cleanup");
