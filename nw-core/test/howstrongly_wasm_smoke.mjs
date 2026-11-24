import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { attachPassageCaches } from "../shells/web/rung-env.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createHowStronglyEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_how_strongly();
assert.equal(task, 1500838626n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.deepEqual(TASK_IDS_BY_CATEGORY[9].slice(0, 3), ["emotion", "which_feeling", "how_strongly"]);

// eqbench.jsonl: a dialogue, who speaks last, four emotions and how
// strongly each is felt. The two dialogues name different speakers, so the
// test can tell which is shown and answer it; the third line is malformed.
const EMOTIONS = ["Happy", "Sad", "Angry", "Afraid"];
const cache = new TextEncoder().encode([
  JSON.stringify({ text: "Ana: The fireworks over the bay were perfect tonight.", who: "Ana",
    emotions: EMOTIONS, scores: [9, 1, 0, 2] }),
  JSON.stringify({ text: "Ben: Someone scratched the whole side of my new car.", who: "Ben",
    emotions: EMOTIONS, scores: [0, 3, 9, 1] }),
  "{not json",
].join("\r\n") + "\n");
// The reference answers: the strongest feeling, and each score on 0, 2,
// ..., 10 with ties going to the lower point.
const STRONGEST = { Ana: "Happy", Ben: "Angry" };
const LEVELS = { Ana: [8, 0, 0, 2], Ben: [0, 2, 8, 0] };
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => api.nw_api_v1_how_strongly_info(handle, BigInt(field));
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
function speaker(shown = frame()) {
  const who = Object.keys(STRONGEST).filter(name => shown.some(command => command.text?.includes(`${name}:`)));
  assert.equal(who.length, 1, JSON.stringify(who));
  return who[0];
}
function has(text) {
  return frame().some(command => command.text === text);
}
function settle(item) {
  for (let i = 0; i < 29 && info(0) === 1n && info(10) === BigInt(item); i++) tick(50);
}
function note(rung) {
  return new TextDecoder().decode(view(api.nw_how_strongly_options_note(pointer, capacity, BigInt(rung))));
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 9n, 2n, 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Which Feeling"));
  assert.ok(menu.some(command => command.text === "How Strongly"));
  assert.equal(note(1), "Rung 1: which emotion is strongest.");
  assert.equal(note(4), "Rung 4: within 8 points of the reference.");
  assert.equal(note(7), "Rung 7: within 4 points of the reference.");
  assert.equal(note(16), "Rung 16: within 0 points of the reference.");
  assert.ok(api.nw_how_strongly_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(has("Press Space or click to start"));
  attachPassageCaches(api, api.nw_how_strongly_load, handle, [cache]);
  assert.equal(dispatch(2, 1), 1n);
  assert.ok(has("How strongly does the character feel each emotion?"));
  for (let item = 0; item < 8; item++) {
    const who = speaker();
    assert.ok(has(`At the end, what does ${who} feel most?`));
    if (item === 0) {
      // Unanswered: a minute passes and it counts wrong.
      for (let i = 0; i < 700 && info(12) === 0n; i++) tick(100);
      assert.equal(info(12), 1n);
      assert.ok(has(`No: ${STRONGEST[who]}`));
    } else {
      click(STRONGEST[who]);
      assert.ok(has(`Right: ${STRONGEST[who]}`));
      if (item === 1) {
        const at = Number(now) / 1000;
        assert.ok(view(api.nw_how_strongly_audio_window(handle, at, at + 0.1, pointer, capacity)).some(byte => byte !== 0));
      }
    }
    settle(item);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(4), 1n);
  assert.equal(info(11), 7n);
  tick(2500);
  assert.equal(info(0), 3n);
  assert.ok(has("1 of 1 passed   highest rung passed 1"));

  // Rung 4: each emotion on the scale, all four within 8 points together.
  assert.equal(api.nw_how_strongly_options_apply(handle, 4n, 1n, 0n), 1n);
  assert.equal(info(1), 4n);
  assert.equal(dispatch(2, 1), 1n);
  for (let item = 0; item < 6; item++) {
    const who = speaker();
    // The first misses Sad and Afraid by 4 each: 8 in all, still within.
    // The second puts both at 10, 18 off, and fails; the rest are exact.
    const picks = LEVELS[who].map((level, index) =>
      index !== 1 && index !== 3 ? level : item === 0 ? level + 4 : item === 1 ? 10 : level);
    const errors = picks.reduce((sum, pick, index) => sum + Math.abs(pick - LEVELS[who][index]), 0);
    for (let step = 0; step < 4; step++) {
      assert.ok(has(`How strongly does ${who} feel: ${EMOTIONS[step]}?  (${step + 1} of 4)`), `${item} ${step}`);
      click(String(picks[step]));
    }
    const truth = EMOTIONS.map((emotion, index) => `${emotion} ${LEVELS[who][index]}`).join(", ");
    assert.ok(has(`${errors <= 8 ? "Right" : "No"}: ${truth}`), `${item} ${errors}`);
    // The scale is gone while the answer shows.
    assert.ok(!has("10"));
    settle(item);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(11) + info(12), 6n);
  assert.equal(info(11), 5n);
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
assert.throws(() => createHowStronglyEnvironment(context, { dialogueCache: "eqbench" }), TypeError);
const environment = createHowStronglyEnvironment(context, {
  seed: 17, rung: 1, trials: 1, frameHz: 20, dialogueCache: cache,
});
try {
  assert.equal(environment.n_actions, 8);
  assert.ok(environment.act(0).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
const largeCache = new TextEncoder().encode(Array.from({ length: 400 }, (_, index) => JSON.stringify({
  text: `Speaker${index}: Line number ${index} with a few more words.`, who: `Speaker${index}`,
  emotions: EMOTIONS, scores: [index % 11, (index + 3) % 11, (index + 6) % 11, (index + 9) % 11],
})).join("\n"));
const memorySizes = [];
for (let index = 0; index < 20; index++) {
  const replay = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 17n);
  try {
    attachPassageCaches(api, api.nw_how_strongly_load, replay, [largeCache]);
    assert.equal(api.nw_how_strongly_agent_event(replay, 0, 8n), 1n);
  } finally {
    assert.equal(api.nw_api_v1_destroy(replay), 0n);
  }
  memorySizes.push(api.memory.buffer.byteLength);
}
assert.equal(memorySizes[1], memorySizes.at(-1), "dialogue cache memory should be reclaimed");
console.log("PASS: How Strongly WASM Emotion tab, saved dialogues, timeout, strongest and scale clicks, tolerance, " +
  "audio, agent controls and cache cleanup");
