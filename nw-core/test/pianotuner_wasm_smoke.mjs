import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

// Piano Tuner through the browser ABI: the hub card, the options note (the
// reference's taskoptions.pianotuner_note), Space starting and Up and Enter
// not; then a rung-1 string turned up by a held Up for a second, down slowly
// by Shift and Down for half of one, up 171 px by a drag with the primary
// button, and said in tune with Enter -- sharp; the two tracks sounding; a
// rung-1 and a two-string rung-10 try tuned by the reference autopilot's
// ports; and the agent's five ports. Every number below is the reference's
// (pianotuner.py driven tick for tick, 50 ms sub-stepped at 1/120 s).

const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createPianoTunerEnvironment } = await instantiateElisa(bytes, { warn: false });
const id = api.nw_api_v1_task_piano_tuner();
assert.equal(id, 994919917n);
assert.equal(api.nw_api_v1_supports(id, 1n), 1n);
const position = TASK_IDS_BY_CATEGORY[3].indexOf("piano_tuner");
assert.equal(position, TASK_IDS_BY_CATEGORY[3].indexOf("by_ear") + 1);

const KEY = { space: 1, enter: 2, up: 4, down: 6, shift: 24 };
const EVENT = { keyDown: 2, keyUp: 3, pointerMove: 4, pointerDown: 5, pointerUp: 6 };
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
let handle = 0n;
let now = 0n;
let sequence = 0n;

function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function texts() {
  const frame = decode(view(api.nw_api_v1_render(handle, pointer, capacity, 1n, 912n, 684n)));
  return frame.filter(command => command.text !== undefined).map(command => command.text);
}
function info(field) {
  return Number(api.nw_api_v1_piano_tuner_info(handle, BigInt(field)));
}
function dispatch(kind, code = 0, flags = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, BigInt(code), 0n, 0n, BigInt(flags), 0n, 0n, 0n);
}
// A pointer event at reference pixels (x, y) from the bottom left; buttons
// is the page's event.buttons.
function pointerAt(kind, x, y, buttons = 0) {
  return api.nw_api_v1_dispatch(handle, BigInt(kind), now, sequence++, 0n, BigInt(buttons), 0n, 0n,
    BigInt(Math.round(x * 1000000 / 912)), BigInt(Math.round(y * 1000000 / 684)), 0n);
}
function tick(dt = 50) {
  now += BigInt(dt);
  return api.nw_api_v1_advance(handle, now, BigInt(dt), sequence++);
}
function silent(begin, end) {
  const length = api.nw_piano_tuner_audio_window(handle, begin, end, pointer, capacity);
  assert.equal(length, BigInt(Math.round((end - begin) * 22050) * 4));
  return view(length).every(byte => byte === 0);
}
// The reference autopilot, one port a tick, from the error and tolerance
// the session reports in thousandths of a cent.
function pilot() {
  const error = info(13);
  const tol = info(16);
  if (Math.abs(error) > 12000) return error > 0 ? 1 : 0;
  if (Math.abs(error) > tol * 0.3) return error > 0 ? 3 : 2;
  return 4;
}
function autopilot() {
  const done = [];
  while (info(0) === 1 && info(8) === 0) {
    const port = pilot();
    assert.equal(api.nw_piano_tuner_agent_event(handle, Number(now) / 1000, BigInt(port)), 1n, String(port));
    if (port === 4) done.push([Number(now), info(12)]);
    else tick();
  }
  tick();
  return done;
}

try {
  handle = api.nw_api_v1_create(id, 1n, 1n, 1n, 1n, 0n, 0n, 0n, 17n);
  assert.ok(handle > 0n);
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 3n, BigInt(position), 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Piano Tuner"));
  const note = new TextDecoder().decode(view(api.nw_piano_tuner_options_note(pointer, capacity, 13n)));
  assert.equal(note, "Rung 13: unison, octave, fifth, fourth, third, within 3.7 cents.");
  assert.ok(api.nw_piano_tuner_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");
  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(api.nw_piano_tuner_audio_window(handle, 0, 0.1, pointer, capacity), 0n, "no sound before the run");

  // Up and Enter do nothing before the run starts; Space starts it.
  assert.equal(dispatch(EVENT.keyDown, KEY.up), 2n);
  assert.equal(dispatch(EVENT.keyDown, KEY.enter), 2n);
  assert.equal(info(0), 0);
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  assert.deepEqual([info(0), info(13), info(14), info(16), info(17)], [1, 132602, 100694, 20000, 0]);
  const shown = texts();
  assert.ok(shown.includes("String 1 of 1: tune it in unison") && shown.includes("rung 1  1/1   within 20.0 cents"),
    shown.join(" | "));
  assert.ok(!silent(0, 0.1), "the reference and the string sound from the start");
  assert.ok(silent(0.4, 0.6), "and are held only a quarter second past their last setting");

  // Up held for a second: 60 cents.
  assert.equal(dispatch(EVENT.keyDown, KEY.up), 1n);
  assert.equal(info(15), 1);
  for (let i = 0; i < 20; i++) tick();
  assert.equal(info(13), 192602);
  assert.ok(!silent(0.4, 0.6), "the tracks go on as the run does");
  assert.equal(dispatch(EVENT.keyUp, KEY.up), 1n);
  // Shift and Down for half a second: 2.5 cents down.
  assert.equal(dispatch(EVENT.keyDown, KEY.shift), 1n);
  assert.equal(dispatch(EVENT.keyDown, KEY.down), 1n);
  assert.equal(info(15), 20);
  for (let i = 0; i < 10; i++) tick();
  assert.equal(info(13), 190102);
  assert.equal(dispatch(EVENT.keyUp, KEY.down), 1n);
  assert.equal(dispatch(EVENT.keyUp, KEY.shift), 1n);
  assert.equal(info(15), 0);
  // A drag 171 px up with the primary button turns it 68.4 cents up; a
  // move without the button ends the drag, and a move after that does
  // nothing. (Heights a quarter of the frame apart arrive exactly.)
  assert.equal(pointerAt(EVENT.pointerDown, 456, 171, 1), 2n);
  assert.equal(pointerAt(EVENT.pointerMove, 456, 342, 1), 1n);
  assert.equal(info(13), 258502);
  assert.equal(pointerAt(EVENT.pointerMove, 456, 513, 0), 2n);
  assert.equal(pointerAt(EVENT.pointerMove, 456, 171, 1), 2n);
  assert.equal(info(13), 258502);
  // Enter: 259 cents sharp.
  assert.equal(dispatch(EVENT.keyDown, KEY.enter), 1n);
  tick();
  assert.deepEqual([info(0), info(8)], [2, 2]);
  assert.ok(texts().includes("259 cents sharp"));
  tick(2499);
  assert.equal(info(0), 2);
  tick(1);
  assert.equal(info(0), 3);
  assert.ok(texts().some(text => text.startsWith("0 of 1 passed")));
  assert.equal(api.nw_api_v1_destroy(handle), 0n);

  // Rung 1 by the autopilot: done at 2.8 s, in tune at +5.9 cents.
  handle = api.nw_api_v1_create(id, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 17n);
  now = 0n;
  assert.equal(pointerAt(EVENT.pointerDown, 456, 100, 1), 1n, "a click starts the run");
  assert.deepEqual(autopilot(), [[2800, 1]]);
  assert.deepEqual([info(0), info(8)], [2, 1]);
  assert.ok(texts().includes("In tune: +5.9 cents"));
  assert.equal(api.nw_api_v1_destroy(handle), 0n);

  // Rung 10: an octave above, then a second string in unison with the first.
  handle = api.nw_api_v1_create(id, 1n, 10n, 1n, 0n, 0n, 0n, 0n, 17n);
  now = 0n;
  assert.equal(dispatch(EVENT.keyDown, KEY.space), 1n);
  assert.deepEqual([info(11), info(17)], [2, 1]);
  assert.ok(texts().includes("String 1 of 2: tune it an octave above"));
  assert.deepEqual(autopilot(), [[4000, 1], [7450, 2]]);
  assert.deepEqual([info(0), info(8), info(10), info(12)], [2, 1, 1, 2]);
  assert.ok(texts().includes("In tune: +1.3 cents"));
} finally {
  if (handle) api.nw_api_v1_destroy(handle);
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
const environment = createPianoTunerEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 5);
  assert.ok(environment.act(0).ok, "the up port");
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("Piano Tuner WASM menu, options note, Space start, a string turned by held keys, Shift, and a drag and "
  + "judged sharp, both tracks sounding, autopilot tries at rungs 1 and 10 in tune, and hold");
