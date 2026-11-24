import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createConductorEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_conductor();
assert.equal(id, 3161448022n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[2].indexOf("conductor");
assert.equal(position, 26);

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
function info(field) {
  return Number(api.nw_api_v1_conductor_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, x = 0, y = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, 0n,
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
}
function tick(dt) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 2n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Conductor"));
  const note = new TextDecoder().decode(view(api.nw_conductor_options_note(pointer, capacity, 16n)));
  assert.equal(note, "Rung 16: 16 beats, 4 cues.  The tempo wanders.");
  assert.ok(frame().some(command => command.text === "Press Space or click to start"));
  assert.equal(api.nw_conductor_options_apply(handle, 1n, 1n, 1n), 1n);
  assert.equal(dispatch(2, 2), 1n);
  assert.equal(info(0), 1);
  assert.ok(frame().some(command => command.text === "Beat 5: bring in the woodwind."));
  assert.equal(dispatch(2, 1), 2n);

  const x = 456;
  const screenY = y => 179 + y * 389 / 640;
  const until = stamp => {
    while (now < BigInt(stamp)) assert.equal(tick(50), 1n);
  };
  for (let beat = 2; beat <= 9; beat++) {
    until(beat * 1000 - 50);
    assert.equal(dispatch(4, 0, x, screenY(400)), 1n);
    until(beat * 1000);
    if (beat === 6) {
      assert.equal(dispatch(5, 0, x, screenY(254.57627118644066)), 1n);
      assert.equal(info(14), 1);
      assert.equal(dispatch(11), 1n);
      assert.equal(info(14), 0);
      const painted = frame();
      assert.ok(painted.some(command => command.text === "woodwind" && command.color === 0xffffffff));
      assert.ok(!painted.some(command => command.text === "Beat 5: bring in the woodwind."));
    } else {
      assert.equal(dispatch(4, 0, x, screenY(300)), 1n);
    }
    until(beat * 1000 + 50);
  }
  assert.equal(info(11), 8);
  assert.equal(info(12), 0);
  assert.ok(view(api.nw_conductor_audio_window(handle, 2, 2.1, pointer, capacity)).some(byte => byte));
  for (let i = 0; i < 35 && info(0) === 1; i++) tick(50);
  assert.equal(info(0), 2);
  assert.equal(info(8), 1);
  assert.equal(info(1), 2);
  assert.ok(frame().some(command => command.text === "Bravo" && command.color === 0x40ff40ff));
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
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
const environment = createConductorEnvironment(context, { seed: 17, rung: 4, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 16);
  assert.ok(environment.act(14).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Conductor WASM menu, options, baton, section cue, PCM, feedback, and stepped environment passed");
