import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

// Night Watch through the browser ABI: the hub card, the options note (the
// reference's taskoptions.nightwatch_note), the night's orders, the four
// separately held turning keys (Left, A, Right, D) and their releases, key
// repeat, the view actually turning the way the held key says along a floor
// wider than the view, a released key's latch running out by itself as the
// reference's does, cancel stopping it at once, a whole night to its
// verdict, the verdict painted the way the info fields say, PCM, and the
// judged hold.

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createNightWatchEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_night_watch();
assert.equal(id, 981902657n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[2].indexOf("night_watch");
assert.equal(position, TASK_IDS_BY_CATEGORY[2].indexOf("shadow_puppets") + 1);

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
  return Number(api.nw_api_v1_night_watch_info(handle, BigInt(field)));
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
  assert.ok(menu.some(command => command.text === "Night Watch"));
  const note = new TextDecoder().decode(view(api.nw_night_watch_options_note(pointer, capacity, 16n)));
  assert.equal(note, "Rung 16: 4 thieves, 3 others.  Read the orders: the colours change.");
  assert.ok(api.nw_night_watch_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  // Rung 7: a floor wider than the view, red caps tonight.
  assert.equal(api.nw_night_watch_options_apply(handle, 7n, 1n, 0n), 1n);

  // Turning keys do nothing before the night starts; Enter starts it.
  assert.equal(dispatch(2, KEY.left), 2n);
  assert.equal(dispatch(2, KEY.enter), 1n);
  assert.equal(info(0), 1);
  assert.ok(texts().includes("Tonight the thieves wear red. The guard wears blue."));
  assert.ok(texts().includes(`caught 0 / ${info(11)}`) && texts().includes("whistle: 6"), texts().join(" | "));
  assert.equal(info(17), 0);

  // Each key is its own bit; a repeat is ignored; releasing one leaves the other.
  assert.equal(dispatch(2, KEY.left), 1n);
  assert.equal(dispatch(2, KEY.a), 1n);
  assert.equal(info(15), 3);
  assert.equal(dispatch(2, KEY.a, 1), 2n);
  assert.equal(dispatch(3, KEY.left), 1n);
  assert.equal(info(15), 2);
  tick(100);
  const left = info(17);
  assert.ok(left < 0, `A held should turn the view left: ${left}`);
  assert.ok(texts().includes("<  A") && texts().includes("D  >"), texts().join(" | "));
  assert.equal(dispatch(3, KEY.a), 1n);
  assert.equal(info(15), 0);
  assert.equal(dispatch(3, KEY.a), 2n);
  // Let go, the view still turns until the key's latch runs out, then stops.
  tick(100);
  assert.ok(info(17) < left, "the latch runs on after the key is let go");
  // Each advance covers at most 0.1 s of the night.
  for (let i = 0; i < 3; i++) tick(100);
  const stopped = info(17);
  tick(100);
  assert.equal(info(17), stopped, "the latch ran out");
  assert.equal(dispatch(2, KEY.right), 1n);
  assert.equal(dispatch(2, KEY.d), 1n);
  assert.equal(info(15), 12);
  tick(100);
  assert.ok(info(17) > stopped, `Right held should turn the view right: ${stopped} -> ${info(17)}`);
  assert.equal(dispatch(11), 1n);
  assert.equal(info(15), 0);
  const settled = info(17);
  tick(100);
  assert.equal(info(17), settled, "cancel let go of the view at once");
  // Space during play is not a turning key and does not restart.
  assert.equal(dispatch(2, KEY.space), 2n);

  // Nobody keeps watch: a thief reaches the safe.
  for (let i = 0; i < 3000 && info(0) === 1; i++) tick(50);
  assert.equal(info(0), 2);
  assert.equal(info(8), 4, "robbed");
  const painted = texts();
  assert.ok(painted.includes("The safe is robbed"), painted.join(" | "));
  let sound = false;
  for (let begin = 0; begin + 1 <= info(9) / 1000 && !sound; begin += 1) {
    const length = api.nw_night_watch_audio_window(handle, begin, begin + 1, pointer, capacity);
    assert.ok(length >= 0n, String(length));
    if (length > 0n) sound = view(length).some(byte => byte);
  }
  assert.ok(sound, "a whole night made no sound");
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
  assert.ok(texts().some(text => text.startsWith("0 of 1 passed")));
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
const environment = createNightWatchEnvironment(context, { seed: 17, rung: 7, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 16);
  assert.ok(environment.act(15).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Night Watch WASM menu, options note, orders, four held turning keys, repeat, latch, cancel, view direction, verdict, PCM, and hold");
