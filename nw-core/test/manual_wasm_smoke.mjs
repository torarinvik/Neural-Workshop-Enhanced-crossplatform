import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createManualEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_manual();
assert.equal(task, 563151331n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(TASK_IDS_BY_CATEGORY[8][2], "manual");

const EVENT = { keyDown: 2n, pointerDown: 5n };
const KEY_CODE = { space: 1, enter: 2 };
const handle = api.nw_api_v1_create(task, 1n, 1n, 3n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => Number(api.nw_api_v1_manual_info(handle, BigInt(field)));
let sequence = 0n;
let now = 0n;
function view(length) {
  assert.ok(length > 0n && length <= capacity, String(length));
  return new Uint8Array(api.memory.buffer, Number(pointer), Number(length));
}
function commands() {
  return decode(view(api.nw_api_v1_render(handle, pointer, capacity, 0n, 912n, 684n)));
}
function texts() {
  return commands().map(command => command.text).filter(Boolean);
}
function dispatch(kind, code = 0, x = 0n, y = 0n, flags = 0n) {
  now += 50n;
  return api.nw_api_v1_dispatch(handle, kind, now, sequence++, BigInt(code), 0n, 0n, flags, x, y, 0n);
}
function key(code, flags = 0n) {
  return dispatch(EVENT.keyDown, code, 0n, 0n, flags);
}
// A press at a window point, y up.
function press(x, y) {
  return dispatch(EVENT.pointerDown, 0, BigInt(Math.round(x * 1000000 / 912)), BigInt(Math.round(y * 1000000 / 684)));
}
function label(words) {
  const found = commands().find(command => command.text === words);
  assert.ok(found, `${words}: ${texts().join(" | ")}`);
  return found;
}
// A switch's name sits just under its body: press a little above it.
function pressSwitch(name) {
  const found = label(name);
  return press(found.a, found.b + found.c * 1.2 + 4);
}
function note(rung) {
  return new TextDecoder().decode(view(api.nw_manual_options_note(pointer, capacity, BigInt(rung))));
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 8n, 0n, 0n, 912n, 684n)));
  for (const name of ["Manual", "Browser", "Errands", "Spreadsheet"]) assert.ok(menu.some(command => command.text === name), name);
  assert.equal(note(1), "Rung 1: 1 steps on a panel of 2 switches, 0 knobs, 1 buttons and 1 lamps.");
  assert.equal(note(30), "Rung 30: 10 steps on a panel of 6 switches, 4 knobs, 6 buttons and 4 lamps.  With steps that " +
    "depend on a lamp, counts read off the display, copying one control to another, pressing until a lamp changes, " +
    "putting controls back as they started, steps that skip the next, controls in shuffled order.");
  assert.ok(api.nw_manual_options_note(pointer, capacity, 3n) < 0n, "rung 3 is not offered");

  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(key(KEY_CODE.enter), 2n, "Enter does nothing before the run");
  assert.equal(key(KEY_CODE.space), 1n);
  assert.deepEqual([info(0), info(1), info(2), info(3), info(9), info(10)], [1, 1, 1, 3, 1, 0]);
  for (const words of ["Manual", "Follow the procedure, then press Finish", "1.  Flip switch S1.", "Finish (Enter)",
    "S1", "S2", "P1", "L1", "display", "rung 1  1/3   1 steps"]) assert.ok(texts().includes(words), words);
  assert.deepEqual(commands().filter(command => command.text === "off" || command.text === "on")
    .sort((one, two) => one.a - two.a).map(command => command.text), ["off", "on"]);

  // S2 there and back, then S1: three moves, and the panel is right.
  assert.equal(pressSwitch("S2"), 1n);
  assert.equal(pressSwitch("S2"), 1n);
  assert.equal(pressSwitch("S1"), 1n);
  assert.equal(info(10), 3);
  assert.equal(press(5, 5), 2n, "a press on nothing does nothing");
  assert.equal(key(KEY_CODE.enter, 1n), 2n, "a repeated Enter is ignored");
  assert.equal(key(KEY_CODE.enter), 1n);
  assert.deepEqual([info(0), info(8), info(4), info(1)], [2, 1, 1, 2]);
  assert.ok(texts().includes("Done exactly as written"));
  assert.equal(pressSwitch("S1"), 2n, "no hands while judged");
  assert.equal(api.nw_manual_options_apply(handle, 1n, 1n, 0n), 2n, "no options mid-run");

  // The verdict holds for 2.5 seconds, then the next procedure at rung 2.
  now += 2000n;
  assert.ok(api.nw_api_v1_advance(handle, now, 2000n, sequence++) > 0n);
  assert.equal(info(0), 2);
  now += 600n;
  assert.ok(api.nw_api_v1_advance(handle, now, 600n, sequence++) > 0n);
  assert.deepEqual([info(0), info(1), info(2), info(10)], [1, 2, 2, 0]);

  // Finish, pressed on screen, with nothing done: never right.
  const finish = label("Finish (Enter)");
  assert.equal(press(finish.a, finish.b), 1n);
  assert.deepEqual([info(0), info(8), info(1)], [2, 2, 1]);
  assert.ok(texts().some(text => text.startsWith("Not as written: ")), texts().join(" | "));
  assert.ok(api.nw_api_v1_read_state(handle, pointer, capacity) > 0n);

  // Agent ports: START is refused mid-run, a frame steps past the verdict,
  // then port 0 flips the first switch drawn.
  assert.equal(api.nw_manual_agent_event(handle, 10.0, 21n), 2n);
  assert.equal(api.nw_manual_agent_event(handle, 10.0, -1n), 1n);
  assert.deepEqual([info(0), info(2)], [1, 3]);
  assert.equal(api.nw_manual_agent_event(handle, 10.0, 0n), 1n);
  assert.equal(info(10), 1);
  assert.equal(api.nw_manual_agent_event(handle, 10.0, 5n), 2n, "no sixth switch at rung 1");
  assert.ok(api.nw_manual_agent_event(handle, 10.0, 22n) < 0n);
  assert.equal(api.nw_manual_agent_event(handle, 9.0, 0n), 2n, "time does not run backwards");
} finally {
  assert.equal(api.nw_api_v1_destroy(handle), 0n);
  api.nw_frame_free(pointer);
}

const canvas = { width: 228, height: 171 };
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {}, moveTo() {}, lineTo() {}, closePath() {},
  clearRect() {}, fillRect() {}, fillText() {}, measureText: () => ({ width: 6 }),
  getImageData: () => ({ data: new Uint8ClampedArray(canvas.width * canvas.height * 4) }),
};
const environment = createManualEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 21);
  assert.ok(environment.act(0).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("PASS: Manual WASM Computer use tab, options notes, switches pressed where they are drawn, Finish by key and " +
  "by press, right and wrong procedures, feedback pause, options and agent controls");
