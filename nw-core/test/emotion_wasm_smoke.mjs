import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createEmotionEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_emotion();
assert.equal(task, 1337504642n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(TASK_IDS_BY_CATEGORY[9][0], "emotion");
assert.equal(api.nw_emotion_load, undefined, "Emotion imports nothing");

const WORDS = ["happy", "sad", "surprised", "angry", "neutral", "afraid", "disgusted", "contemptuous"];
const ASK = "Which emotion is this face showing?";
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => api.nw_api_v1_emotion_info(handle, BigInt(field));
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
  return new TextDecoder().decode(view(api.nw_emotion_options_note(pointer, capacity, BigInt(rung))));
}
function count(kind) {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n))).filter(command => command.kind === kind).length;
}
const POLYGON = 8;
const LINE = 6;
function settle(item) {
  for (let i = 0; i < 29 && info(0) === 1n && info(10) === BigInt(item); i++) tick(50);
}
// Plays a round pressing 1 to every face but the first, which runs out of
// time; checks each question and that the feedback names offered answers.
// The round ends early once too many are wrong to pass. With a flash, the
// first face is covered once its moment ends. Two-step items answer 1 twice.
function playRound(items, options, ask, flash) {
  for (let item = 0; item < items && info(0) === 1n; item++) {
    const shown = texts();
    assert.equal(shown.filter(text => text === ASK).length, 1, shown.join(" | "));
    assert.ok(shown.some(text => text.startsWith(ask)), shown.join(" | "));
    const offered = shown.filter(text => WORDS.includes(text));
    assert.equal(offered.length, options, shown.join(" | "));
    const before = info(11);
    if (item === 0) {
      // The face draws its brows or its mouth (or both) as lines; uncropped,
      // an oval and two eyes too.
      const lines = count(LINE);
      if (flash === 0) assert.ok(count(POLYGON) >= 3, "a whole drawn face");
      assert.ok(!texts().includes("?"));
      if (flash > 0) {
        while (Number(info(9)) / 1000 < flash + 0.05) tick(50);
        assert.ok(texts().includes("?"), "covered after its moment");
        assert.ok(lines - count(LINE) >= 2, `the face's lines are gone: ${lines} ${count(LINE)}`);
      }
      for (let i = 0; i < 400 && info(12) === 0n; i++) tick(100);
      assert.equal(info(12), 1n);
    } else {
      assert.equal(dispatch(2, 12), 1n);
      if (info(0) === 1n && !texts().some(text => text.startsWith("Right: ") || text.startsWith("No: "))) {
        assert.ok(texts().some(text => text.includes("(2 of 2)")));
        assert.equal(dispatch(2, 12), 1n);
      }
    }
    const verdict = texts().find(text => text.startsWith("Right: ") || text.startsWith("No: "));
    assert.ok(verdict, String(item));
    const right = verdict.startsWith("Right: ");
    assert.equal(info(11) - before, right ? 1n : 0n);
    const named = verdict.slice(right ? 7 : 4).split(", then ");
    assert.ok(named.every(word => WORDS.includes(word)), verdict);
    settle(item);
  }
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 9n, 0n, 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Tone of Voice"));
  assert.ok(menu.some(command => command.text === "Which Feeling"));
  assert.ok(menu.some(command => command.text === "Emotion"));
  assert.equal(note(1), "Rung 1: 2 emotions to tell apart.");
  assert.equal(note(4), "Rung 4: 7 emotions to tell apart.");
  assert.equal(note(7), "Rung 7: 8 emotions to tell apart.");
  assert.ok(api.nw_emotion_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(dispatch(2, 1), 1n);
  playRound(12, 2, "Which emotion is this?", 0);
  assert.equal(info(0), 2n);
  assert.ok(info(12) >= 1n && info(11) + info(12) <= 12n, `${info(11)} ${info(12)}`);
  tick(2500);
  assert.equal(info(0), 3n);

  // Rung 20: two emotions in each face, shown for a moment.
  assert.equal(api.nw_emotion_options_apply(handle, 20n, 1n, 0n), 1n);
  assert.equal(info(6), 20n);
  assert.equal(dispatch(2, 1), 1n);
  playRound(12, 8, "Which emotion is strongest?  (1 of 2)", 0.15);
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
const environment = createEmotionEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 8);
  assert.ok(environment.act(0).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("PASS: Emotion WASM Emotion tab, options notes, drawn faces, flash cover, two-step answers, timeout, keys, " +
  "feedback, options and agent controls");
