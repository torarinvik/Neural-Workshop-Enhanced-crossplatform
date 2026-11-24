import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createWhyTheyFeelEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_why_they_feel();
assert.equal(task, 3835238973n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(TASK_IDS_BY_CATEGORY[9][4], "why_they_feel");
assert.equal(api.nw_why_they_feel_load, undefined, "Why They Feel imports nothing");

const WORDS = ["happy", "sad", "hopeful", "worried", "relieved", "disappointed", "proud", "ashamed", "remorseful",
  "admiring", "disapproving", "grateful", "angry", "glad for them", "sorry for them", "resentful", "gloating"];
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => api.nw_api_v1_why_they_feel_info(handle, BigInt(field));
let sequence = 0n;
let now = 0n;
function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function texts() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n))).map(command => command.text).filter(Boolean);
}
function dispatch(kind, code = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, 0n, 0n, 0n, 0n);
}
function tick(dt) {
  now += BigInt(dt);
  assert.ok(api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++) > 0n);
}
function note(rung) {
  return new TextDecoder().decode(view(api.nw_why_they_feel_options_note(pointer, capacity, BigInt(rung))));
}
function settle(item) {
  for (let i = 0; i < 29 && info(0) === 1n && info(10) === BigInt(item); i++) tick(50);
}
// Plays a round pressing 1 to every story but the first, which runs out of
// time; checks each question and that the feedback names an offered answer.
// The round ends early once too many are wrong to pass.
function playRound(items, options, question) {
  for (let item = 0; item < items && info(0) === 1n; item++) {
    const shown = texts();
    const asked = shown.filter(text => question.test(text));
    assert.equal(asked.length, 1, shown.join(" | "));
    const offered = shown.filter(text => WORDS.includes(text));
    assert.equal(offered.length, options, shown.join(" | "));
    const before = info(11);
    if (item === 0) {
      for (let i = 0; i < 400 && info(12) === 0n; i++) tick(100);
      assert.equal(info(12), 1n);
    } else {
      assert.equal(dispatch(2, 12), 1n);
    }
    const verdict = texts().find(text => text.startsWith("Right: ") || text.startsWith("No: "));
    assert.ok(verdict, String(item));
    const right = verdict.startsWith("Right: ");
    assert.ok(offered.includes(verdict.slice(right ? 7 : 4)), verdict);
    assert.equal(info(11) - before, right ? 1n : 0n);
    if (right) assert.equal(verdict.slice(7), offered[0], "1 is the first answer");
    if (item === 1) {
      // Cue times run on the round's own clock (field 9, in milliseconds).
      const at = Number(info(9)) / 1000;
      assert.ok(view(api.nw_why_they_feel_audio_window(handle, at, at + 0.1, pointer, capacity)).some(byte => byte !== 0));
    }
    settle(item);
  }
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 9n, 4n, 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Why They Feel"));
  assert.ok(menu.some(command => command.text === "Emotion"));
  assert.equal(note(1), "Rung 1: 2 answers to choose from.");
  assert.equal(note(7), "Rung 7: 5 answers to choose from.");
  assert.equal(note(13), "Rung 13: 8 answers to choose from.");
  assert.ok(api.nw_why_they_feel_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(dispatch(2, 1), 1n);
  assert.ok(texts().includes("What would anyone feel, in their place?"));
  playRound(10, 2, /^How does \S+ feel\?$/);
  assert.equal(info(0), 2n);
  assert.ok(info(12) >= 2n && info(11) + info(12) <= 10n, `${info(11)} ${info(12)}`);
  tick(2500);
  assert.equal(info(0), 3n);

  // Rung 20: stories of who has heard what, two levels deep.
  assert.equal(api.nw_why_they_feel_options_apply(handle, 20n, 1n, 0n), 1n);
  assert.equal(info(6), 20n);
  assert.equal(dispatch(2, 1), 1n);
  playRound(10, 8, /^(How does \S+ feel\?|What does \S+ think \S+ thinks \S+ feels\?)$/);
  assert.equal(info(0), 2n);
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
const environment = createWhyTheyFeelEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 8);
  assert.ok(environment.act(0).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("PASS: Why They Feel WASM Emotion tab, options notes, timeout, keys, feedback, belief questions, audio, " +
  "options and agent controls");
