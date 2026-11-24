import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { attachPassageCaches } from "../shells/web/rung-env.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createReadingPeopleEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_reading_people();
assert.equal(task, 249251215n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(TASK_IDS_BY_CATEGORY[9][3], "reading_people");

// emobench.jsonl: two stories to understand, with different subjects so
// the test can tell which is shown, one to act on, and a malformed line.
const story = fields => JSON.stringify(fields);
const cache = new TextEncoder().encode([
  story({ kind: "understand", scenario: "Ana's brother ran to hug her at the finish line.", subject: "Ana",
    choices: ["Shame", "Touched", "Anger", "Boredom"], answer: "Touched",
    causes: ["She finished last", "Her brother came", "The race was long"], cause: "Her brother came" }),
  story({ kind: "understand", scenario: "Ben's new bike was stolen from the station.", subject: "Ben",
    choices: ["Upset", "Proud", "Bored", "Amused"], answer: "Upset",
    causes: ["His bike was stolen", "The train was late", "It rained"], cause: "His bike was stolen" }),
  story({ kind: "act", scenario: "Omar's new colleague eats lunch alone every day.", subject: "Omar",
    choices: ["Ignore it", "Invite the colleague to lunch", "Tell the manager", "Joke about it"],
    answer: "Invite the colleague to lunch" }),
  "{not json",
].join("\r\n") + "\n");
const FEELS = { Ana: "Touched", Ben: "Upset" };
const WHY = { Ana: "Her brother came", Ben: "His bike was stolen" };
const WRONG = { Ana: "The race was long", Ben: "It rained" };
const handle = api.nw_api_v1_create(task, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => api.nw_api_v1_reading_people_info(handle, BigInt(field));
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
function has(text) {
  return frame().some(command => command.text === text);
}
function subject() {
  const shown = frame();
  const who = Object.keys(FEELS).filter(name => shown.some(command => command.text?.includes(`${name}'s`)));
  assert.equal(who.length, 1, JSON.stringify(who));
  return who[0];
}
function settle(item) {
  for (let i = 0; i < 29 && info(0) === 1n && info(10) === BigInt(item); i++) tick(50);
}
function note(rung) {
  return new TextDecoder().decode(view(api.nw_reading_people_options_note(pointer, capacity, BigInt(rung))));
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 9n, 3n, 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Reading People"));
  assert.ok(menu.some(command => command.text === "Why They Feel"));
  assert.equal(note(1), "Rung 1: feel.");
  assert.equal(note(4), "Rung 4: why.");
  assert.equal(note(7), "Rung 7: act.");
  assert.equal(note(10), "Rung 10: feel, why, act.");
  assert.ok(api.nw_reading_people_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(has("Press Space or click to start"));
  attachPassageCaches(api, api.nw_reading_people_load, handle, [cache]);
  assert.equal(dispatch(2, 1), 1n);
  assert.ok(has("Read the story: how do they feel, why, what helps?"));
  for (let item = 0; item < 6; item++) {
    const who = subject();
    assert.ok(has(`How does ${who} feel?`));
    if (item === 0) {
      // Unanswered: 45 seconds pass and it counts wrong.
      for (let i = 0; i < 600 && info(12) === 0n; i++) tick(100);
      assert.equal(info(12), 1n);
      assert.ok(has(`No: ${FEELS[who]}`));
    } else {
      click(FEELS[who]);
      assert.ok(has(`Right: ${FEELS[who]}`));
      if (item === 1) {
        const at = Number(now) / 1000;
        assert.ok(view(api.nw_reading_people_audio_window(handle, at, at + 0.1, pointer, capacity)).some(byte => byte !== 0));
      }
    }
    settle(item);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(4), 1n);
  assert.equal(info(11), 5n);
  tick(2500);
  assert.equal(info(0), 3n);
  assert.ok(has("1 of 1 passed   highest rung passed 1"));

  // Rung 4: how they feel, then why; an item is right only when both are.
  assert.equal(api.nw_reading_people_options_apply(handle, 4n, 1n, 0n), 1n);
  assert.equal(dispatch(2, 1), 1n);
  for (let item = 0; item < 6; item++) {
    const who = subject();
    assert.ok(has(`How does ${who} feel?  (1 of 2)`), String(item));
    click(FEELS[who]);
    assert.ok(has("Why?  (2 of 2)"), String(item));
    // The first gets the cause wrong.
    click(item === 0 ? WRONG[who] : WHY[who]);
    assert.ok(has(`${item === 0 ? "No" : "Right"}: ${FEELS[who]}: ${WHY[who]}`), String(item));
    settle(item);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(11), 5n);
  tick(2500);

  // Rung 7: the most helpful thing to do, answered with its number key.
  assert.equal(api.nw_reading_people_options_apply(handle, 7n, 1n, 0n), 1n);
  assert.equal(dispatch(2, 1), 1n);
  assert.ok(has("What would be most helpful for Omar to do?"));
  // Choices keep the file's order, so the second answer is key 2.
  assert.equal(dispatch(2, 13), 1n);
  assert.ok(has("Right: Invite the colleague to lunch"));
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
assert.throws(() => createReadingPeopleEnvironment(context, { storyCache: "emobench" }), TypeError);
const environment = createReadingPeopleEnvironment(context, {
  seed: 17, rung: 1, trials: 1, frameHz: 20, storyCache: cache,
});
try {
  assert.equal(environment.n_actions, 8);
  assert.ok(environment.act(0).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
const largeCache = new TextEncoder().encode(Array.from({ length: 400 }, (_, index) => JSON.stringify({
  kind: index % 2 ? "act" : "understand", scenario: `Story number ${index} with a few more words.`, subject: `Person${index}`,
  choices: ["One", "Two", "Three", "Four"], answer: "Two", causes: ["A", "B"], cause: "B",
})).join("\n"));
const memorySizes = [];
for (let index = 0; index < 20; index++) {
  const replay = api.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 17n);
  try {
    attachPassageCaches(api, api.nw_reading_people_load, replay, [largeCache]);
    assert.equal(api.nw_reading_people_agent_event(replay, 0, 8n), 1n);
  } finally {
    assert.equal(api.nw_api_v1_destroy(replay), 0n);
  }
  memorySizes.push(api.memory.buffer.byteLength);
}
assert.equal(memorySizes[1], memorySizes.at(-1), "story cache memory should be reclaimed");
console.log("PASS: Reading People WASM Emotion tab, saved stories, timeout, feel, why and act answers, " +
  "audio, agent controls and cache cleanup");
