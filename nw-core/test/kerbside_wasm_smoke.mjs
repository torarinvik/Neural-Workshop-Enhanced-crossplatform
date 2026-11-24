import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

// Kerbside through the browser ABI: the hub card, the options note (the
// reference's taskoptions.kerbside_note), Space and only Space starting, the
// four separately held walking keys (Up, W, Down, S) and their releases, key
// repeat, the kerb holding a walker who steps back, walking winning over
// stepping back, cancel, a walker who does not listen struck in lane 1, the
// street painted the way the info fields say, the live sound of the street
// bit for bit against kerbside.py -- the engines, and the crash -- the
// judged hold, and the agent's two ports.

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createKerbsideEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_kerbside();
assert.equal(id, 1420277302n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[2].indexOf("kerbside");
assert.equal(position, TASK_IDS_BY_CATEGORY[2].indexOf("night_watch") + 1);

const KEY = { space: 1, enter: 2, up: 4, down: 6, w: 77, s: 78 };
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
  return Number(api.nw_api_v1_kerbside_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, BigInt(flags), 0n, 0n, 0n);
}
function tick(dt) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}
// kerbside.mix over this window of the run below, as sha256.
function heard(begin, end) {
  const length = api.nw_kerbside_audio_window(handle, begin, end, pointer, capacity);
  assert.ok(length > 0n, String(length));
  return createHash("sha256").update(view(length)).digest("hex");
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 2n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Kerbside"));
  const note = new TextDecoder().decode(view(api.nw_kerbside_options_note(pointer, capacity, 10n)));
  assert.equal(note, "Rung 10: 4 lane(s).  Quiet electric cars.  Wind.");
  assert.ok(api.nw_kerbside_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(api.nw_kerbside_options_apply(handle, 1n, 1n, 0n), 1n);

  // Walking keys do nothing before the run starts, nor does Enter; Space starts it.
  assert.equal(dispatch(2, KEY.up), 2n);
  assert.equal(dispatch(2, KEY.enter), 2n);
  assert.equal(info(0), 0);
  assert.equal(dispatch(2, KEY.space), 1n);
  assert.equal(info(0), 1);
  const playing = texts();
  assert.ok(playing.includes("Cross when the way is clear -- by ear") && playing.includes("rung 1  1/1   1 lanes"),
    playing.join(" | "));
  assert.equal(info(10), 1);
  assert.equal(info(11), -1200);

  // Stepping back on the kerb goes nowhere; walking wins over stepping back.
  assert.equal(dispatch(2, KEY.down), 1n);
  assert.equal(info(14), 4);
  tick(50);
  assert.equal(info(11), -1200);
  assert.equal(dispatch(2, KEY.up), 1n);
  assert.equal(info(14), 5);
  tick(50);
  assert.equal(info(11), -1130);
  assert.equal(dispatch(3, KEY.up), 1n);
  assert.equal(dispatch(3, KEY.down), 1n);
  assert.equal(info(14), 0);
  assert.equal(dispatch(3, KEY.down), 2n);
  tick(50);
  assert.equal(info(11), -1130, "a let-go key stops the walker at once");
  // W and S are their own keys; a repeat is ignored; cancel lets go of all.
  assert.equal(dispatch(2, KEY.w), 1n);
  assert.equal(dispatch(2, KEY.w, 1), 2n);
  assert.equal(dispatch(2, KEY.s), 1n);
  assert.equal(info(14), 10);
  assert.equal(dispatch(3, KEY.s), 1n);
  assert.equal(info(14), 2);
  assert.equal(dispatch(11), 1n);
  assert.equal(info(14), 0);
  tick(50);
  assert.equal(info(11), -1130);

  // A walker who does not listen: W held from here on, struck in lane 1.
  assert.equal(dispatch(2, KEY.w), 1n);
  for (let i = 0; i < 400 && info(0) === 1; i++) tick(50);
  assert.equal(info(0), 2);
  assert.equal(info(8), 2, "hit");
  assert.equal(info(15), 1);
  assert.equal(info(9), 1221);
  assert.equal(now, 1250n);
  const painted = texts();
  assert.ok(painted.includes("Hit in lane 1"), painted.join(" | "));
  // The street's sound, the passing car's engine and then the crash, as
  // kerbside.mix makes it for the same run; asked again from the start, the
  // same.
  const engine = "a8ca43bbcf2b23de5a55e0b430c1bf87d182cd6a6a91af79ff9ec2b2284988fa";
  assert.equal(heard(0.5, 0.6), engine);
  assert.equal(heard(1.0, 1.1), "ee934a11255cce398a0a67411a7f96f716e6e8468c433cf0a602d889502101eb");
  assert.equal(heard(1.2, 1.3), "bf37c43b46f0b28ad1b599f9919067c3f30b462606ebba5688bd6cdab6f0e783");
  assert.equal(heard(0.5, 0.6), engine);
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
  assert.ok(texts().some(text => text.startsWith("0 of 1 passed")));
  assert.equal(api.nw_kerbside_audio_window(handle, 0.5, 0.6, pointer, capacity), 0n);
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
const environment = createKerbsideEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 2);
  assert.ok(environment.act(0).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Kerbside WASM menu, options note, Space start, four held walking keys, repeat, kerb, cancel, a struck walker, live sound bit for bit, and hold");
