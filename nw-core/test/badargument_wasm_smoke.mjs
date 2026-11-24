import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { attachPassageCaches } from "../shells/web/rung-env.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createBadArgumentEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_bad_argument();
assert.equal(task, 2769191638n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.deepEqual(TASK_IDS_BY_CATEGORY[11], ["bad_argument", "second_thoughts"]);

// Imported fallacy questions say their own answer, so the test can answer
// them; the options in the file are ignored, as in the reference.
const cache = new TextEncoder().encode(Array.from({ length: 12 }, (_, index) =>
  JSON.stringify({ kind: "fallacy", prompt: `Imported ${index} ${index % 2 ? "no" : "yes"}`, ask: "Valid?",
    options: ["ignored", "options"], answer: index % 2 })).join("\n"));
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let handle = 0n;
let sequence = 0n;
let now = 0n;
const info = field => api.nw_api_v1_bad_argument_info(handle, BigInt(field));
function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function texts() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)))
    .map(command => command.text).filter(Boolean);
}
function dispatch(kind, code = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, 0n, 0n, 0n, 0n);
}
function tick(dt) {
  now += BigInt(dt);
  assert.ok(api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++) > 0n);
}
function note(rung) {
  return new TextDecoder().decode(view(api.nw_bad_argument_options_note(pointer, capacity, BigInt(rung))));
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 11n, 0n, 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Bad Argument"));
  assert.ok(menu.some(command => command.text === "Second Thoughts"));
  assert.equal(note(1), "Rung 1: nonsense.");
  assert.equal(note(10), "Rung 10: world, world, fallacy.  Name what is wrong.");
  assert.equal(note(13), "Rung 13: world, chain, fallacy, formal.");
  assert.ok(api.nw_bad_argument_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");

  // Rung 1: pressing 1 to every question fails the round.
  handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n);
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(dispatch(2, 1), 1n);
  assert.equal(info(0), 1n);
  assert.ok(texts().includes("Does the conclusion follow from what is given?"));
  let first = true;
  for (let i = 0; i < 800 && info(0) === 1n; i++) {
    if (info(11) + info(12) === info(10) && dispatch(2, 12) === 1n && first) {
      const shown = texts();
      assert.ok(shown.some(text => text.startsWith("Right: ") || text.startsWith("No: ")), shown.join(" | "));
      assert.ok(view(api.nw_bad_argument_audio_window(handle, 0, 0.1, pointer, capacity)).some(byte => byte !== 0));
      first = false;
    }
    tick(50);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(4), 0n);
  tick(2500);
  assert.equal(info(0), 3n);
  assert.ok(texts().includes("0 of 1 passed   highest rung passed 0"));
  assert.equal(api.nw_api_v1_destroy(handle), 0n);

  // Rung 7 mixes in the imported fallacies.
  handle = api.nw_api_v1_create(task, 1n, 7n, 1n, 0n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n);
  attachPassageCaches(api, api.nw_bad_argument_load, handle, [cache]);
  assert.equal(api.nw_bad_argument_options_apply(handle, 7n, 1n, 0n), 1n);
  assert.equal(info(6), 7n);
  assert.equal(dispatch(2, 1), 1n);
  let imported = 0;
  for (let i = 0; i < 1600 && info(0) === 1n; i++) {
    if (info(11) + info(12) === info(10)) {
      const shown = texts().find(text => text.startsWith("Imported "));
      if (shown) {
        imported++;
        assert.ok(texts().includes("it follows") && texts().includes("it does not follow"));
        assert.equal(dispatch(2, shown.endsWith("yes") ? 12 : 13), 1n);
        assert.ok(texts().some(text => text.startsWith("Right: ")), shown);
      } else {
        dispatch(2, 12);
      }
    }
    tick(50);
  }
  assert.ok(imported >= 2, String(imported));
} finally {
  if (handle > 0n) api.nw_api_v1_destroy(handle);
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
const environment = createBadArgumentEnvironment(context, {
  seed: 17, rung: 7, trials: 1, frameHz: 20, questionCache: cache,
});
try {
  assert.equal(environment.n_actions, 8);
  assert.ok(environment.act(0).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
const largeCache = new TextEncoder().encode(Array.from({ length: 200 }, (_, index) =>
  JSON.stringify({ kind: index % 2 ? "formal" : "fallacy", prompt: `Argument ${index}`, ask: "Valid?",
    options: ["yes", "no"], answer: index % 2 })).join("\n"));
const memorySizes = [];
for (let index = 0; index < 20; index++) {
  const replay = api.nw_api_v1_create(task, 1n, 13n, 1n, 0n, 0n, 0n, 0n, 17n);
  try {
    attachPassageCaches(api, api.nw_bad_argument_load, replay, [largeCache]);
    assert.equal(api.nw_bad_argument_agent_event(replay, 0, 8n), 1n);
  } finally {
    assert.equal(api.nw_api_v1_destroy(replay), 0n);
  }
  memorySizes.push(api.memory.buffer.byteLength);
}
assert.equal(memorySizes[1], memorySizes.at(-1), "question cache memory should be reclaimed");
console.log("PASS: Bad Argument WASM Rationality tab, options notes, keys, a fixed answer's failed round, imported " +
  "fallacies, audio, agent controls and cache cleanup");
