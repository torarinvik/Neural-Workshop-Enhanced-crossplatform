import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

// Air Hockey through the browser ABI: the hub card, the options note (the
// reference's taskoptions.airhockey_note text), the four separately held bar
// keys (Left, A, Right, D) and their releases, key repeat, cancel, the bar
// actually sliding the way the held key says, a whole game to its verdict,
// the verdict painted the way the info fields say, PCM, and the judged hold.

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createAirHockeyEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_air_hockey();
assert.equal(id, 1330898689n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[2].indexOf("air_hockey");
assert.equal(position, TASK_IDS_BY_CATEGORY[2].indexOf("lock_pick") + 1);

const KEY = { space: 1, enter: 2, left: 3, right: 5, a: 99, d: 100 };
const handle = api.nw_api_v1_create(id, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let now = 0n;
let sequence = 0n;

function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function frame() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)));
}
function texts() {
  return frame().filter(command => command.text !== undefined).map(command => command.text);
}
function info(field) {
  return Number(api.nw_api_v1_air_hockey_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, BigInt(flags), 0n, 0n, 0n);
}
function tick(dt) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 2n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Air Hockey"));
  const note = new TextDecoder().decode(view(api.nw_air_hockey_options_note(pointer, capacity, 16n)));
  assert.equal(note, "Rung 16: first to 3; 2 against loses.  The camera swings.  At times you look from the far end.");
  assert.ok(api.nw_air_hockey_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(api.nw_air_hockey_options_apply(handle, 1n, 1n, 1n), 1n);

  // Bar keys do nothing before the game starts; Enter starts it.
  assert.equal(dispatch(2, KEY.left), 2n);
  assert.equal(dispatch(2, KEY.enter), 1n);
  assert.equal(info(0), 1);
  assert.ok(texts().includes("Score in the far goal; keep the puck out of yours"));

  // Each key is its own bit; a repeat is ignored; releasing one leaves the other.
  assert.equal(dispatch(2, KEY.left), 1n);
  assert.equal(dispatch(2, KEY.a), 1n);
  assert.equal(info(15), 3);
  assert.equal(dispatch(2, KEY.a, 1), 2n);
  assert.equal(dispatch(3, KEY.left), 1n);
  assert.equal(info(15), 2);
  const start = info(16);
  tick(100);
  assert.ok(info(16) < start, `A held should slide the bar left: ${start} -> ${info(16)}`);
  assert.equal(dispatch(3, KEY.a), 1n);
  assert.equal(info(15), 0);
  assert.equal(dispatch(3, KEY.a), 2n);
  assert.equal(dispatch(2, KEY.right), 1n);
  assert.equal(dispatch(2, KEY.d), 1n);
  assert.equal(info(15), 12);
  const left = info(16);
  tick(100);
  assert.ok(info(16) > left, `Right held should slide the bar right: ${left} -> ${info(16)}`);
  assert.equal(dispatch(11), 1n);
  assert.equal(info(15), 0);
  const settled = info(16);
  tick(100);
  assert.equal(info(16), settled, "cancel let go of the bar");
  // Space during play is not a bar key and does not restart.
  assert.equal(dispatch(2, KEY.space), 2n);

  // Nobody holds the mallet: the game runs out to a verdict.
  for (let i = 0; i < 2000 && info(0) === 1; i++) tick(50);
  assert.equal(info(0), 2);
  const result = info(8);
  const [mine, theirs] = [info(10), info(11)];
  const painted = texts();
  const verdict = result === 1 ? `You win ${mine}-${theirs}` : `You lose ${mine}-${theirs}`;
  assert.ok(painted.includes(verdict) || painted.includes("Time: no winner"), painted.join(" | "));
  assert.ok(painted.includes(`them ${theirs} / ${info(13)}`), painted.join(" | "));
  let sound = false;
  for (let begin = 0; begin + 1 <= info(9) / 1000 && !sound; begin += 1) {
    const length = api.nw_air_hockey_audio_window(handle, begin, begin + 1, pointer, capacity);
    assert.ok(length >= 0n, String(length));
    if (length > 0n) sound = view(length).some(byte => byte);
  }
  assert.ok(sound, "a whole game made no sound");
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
  assert.ok(texts().some(text => text.startsWith(`${result === 1 ? 1 : 0} of 1 passed`)));
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
const environment = createAirHockeyEnvironment(context, { seed: 17, rung: 4, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 16);
  assert.ok(environment.act(15).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Air Hockey WASM menu, options note, four held bar keys, repeat, cancel, bar direction, verdict, PCM, and hold");
