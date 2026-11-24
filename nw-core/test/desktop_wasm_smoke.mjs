import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createDesktopEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_desktop();
assert.equal(task, 3716188083n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.deepEqual(TASK_IDS_BY_CATEGORY[8].slice(0, 6), ["desktop", "forms", "manual", "browser", "errands", "spreadsheet"]);

const EVENT = { keyDown: 2n, pointerMove: 4n, pointerDown: 5n, pointerUp: 6n, text: 8n };
const KEY_CODE = { space: 1, enter: 2, left: 3, up: 4, right: 5, down: 6 };
const MODIFIER = { none: 0n, shift: 1n, alt: 4n };
const DESK = 0x466682ff;
const handle = api.nw_api_v1_create(task, 1n, 1n, 3n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => Number(api.nw_api_v1_desktop_info(handle, BigInt(field)));
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
function dispatch(kind, code = 0, x = 0n, y = 0n, modifiers = 0n, value = 0n) {
  now += 50n;
  return api.nw_api_v1_dispatch(handle, kind, now, sequence++, BigInt(code), value, modifiers, 0n, x, y, 0n);
}
function key(code, modifiers = MODIFIER.none) {
  return dispatch(EVENT.keyDown, code, 0n, 0n, modifiers);
}
function letter(character) {
  return dispatch(EVENT.text, 0, 0n, 0n, 0n, BigInt(character.codePointAt(0)));
}
// The desktop's own frame: its background gives where screen units land.
function screen() {
  const desk = commands().find(command => command.color === DESK);
  assert.ok(desk, "the desktop is drawn");
  const scale = desk.c / 1000;
  return { left: desk.a, top: desk.b + desk.d, scale };
}
// A mouse event at a point in the desktop's units (y down).
function mouse(kind, x, y, button = 0) {
  const frame = screen();
  const px = frame.left + x * frame.scale;
  const py = frame.top - y * frame.scale;
  return dispatch(kind, button, BigInt(Math.round(px * 1000000 / 912)), BigInt(Math.round(py * 1000000 / 684)));
}
function note(rung) {
  return new TextDecoder().decode(view(api.nw_desktop_options_note(pointer, capacity, BigInt(rung))));
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 8n, 0n, 0n, 912n, 684n)));
  for (const name of ["Desktop", "Forms", "Manual", "Browser", "Errands", "Spreadsheet"])
    assert.ok(menu.some(command => command.text === name), name);
  assert.equal(note(1), "Rung 1: 1 window(s), 1 setting(s) to reach.");
  assert.ok(note(30).startsWith("Rung 30: 6 window(s), 14 setting(s) to reach.  With tabs, scrolling,"), note(30));
  assert.ok(note(30).endsWith("a card that hides.  You must beat the reference."), note(30));
  assert.ok(api.nw_desktop_options_note(pointer, capacity, 7n) < 0n, "rung 7 is not offered");

  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(key(KEY_CODE.enter), 2n, "Enter does nothing before the run");
  assert.equal(letter("r"), 2n, "no right click before the run");
  assert.equal(key(KEY_CODE.space), 1n);
  assert.deepEqual([info(0), info(1), info(2), info(3), info(9), info(10), info(11), info(13)], [1, 1, 1, 3, 0, 40, 32, 1]);
  for (const words of ["Desktop", "Reach the settings on the card in 4 clicks or fewer, then Done", "Set these:",
    "•  Files › Duplex: off", "Files", "Duplex", "Start", "Done", "rung 1  1/3  clicks 0  par 4  out of clicks at 32"])
    assert.ok(texts().includes(words), `${words}: ${texts().join(" | ")}`);

  // Arrows step the pointer from (500, 320) to the switch at (495, 110):
  // Shift a long step, none a medium one, Alt a short one.
  for (const modifiers of [MODIFIER.shift, MODIFIER.shift, MODIFIER.none, MODIFIER.none, MODIFIER.alt, MODIFIER.alt])
    assert.equal(key(KEY_CODE.up, modifiers), 1n);
  assert.equal(key(KEY_CODE.left, MODIFIER.alt), 1n);
  assert.equal(info(9), 0, "moving is free");
  assert.equal(key(KEY_CODE.space), 1n);
  assert.deepEqual([info(9), info(12)], [1, 1]);
  assert.ok(texts().includes("✓ Files › Duplex: off"));
  assert.equal(key(KEY_CODE.enter), 1n);
  assert.deepEqual([info(0), info(8), info(4), info(1)], [2, 1, 1, 2]);
  assert.ok(texts().includes("1 of 1 settings in 1 clicks; par was 4"));
  assert.equal(key(KEY_CODE.space), 2n, "no clicks while judged");
  assert.equal(api.nw_desktop_options_apply(handle, 1n, 1n, 0n), 2n, "no options mid-run");

  // The verdict holds for 2.2 seconds, then the next round at rung 2.
  now += 2000n;
  assert.ok(api.nw_api_v1_advance(handle, now, 2000n, sequence++) > 0n);
  assert.equal(info(0), 2);
  now += 400n;
  assert.ok(api.nw_api_v1_advance(handle, now, 400n, sequence++) > 0n);
  assert.deepEqual([info(0), info(1), info(2), info(9)], [1, 2, 2, 0]);

  // The mouse: a right click costs one; D presses and lets go; a press and
  // a release a little apart on Done is a click there, and the round ends.
  assert.equal(mouse(EVENT.pointerMove, 300, 300), 1n);
  assert.equal(mouse(EVENT.pointerDown, 300, 300, 2), 1n);
  assert.equal(info(9), 1);
  assert.equal(letter("d"), 1n);
  assert.equal(info(15), 1, "held");
  assert.equal(letter("D"), 1n);
  assert.deepEqual([info(15), info(9)], [0, 2]);
  assert.equal(mouse(EVENT.pointerDown, 930, 620), 1n);
  assert.equal(info(15), 1);
  assert.equal(mouse(EVENT.pointerUp, 931, 621), 1n);
  assert.deepEqual([info(0), info(8), info(9)], [2, 2, 3]);
  assert.ok(api.nw_api_v1_read_state(handle, pointer, capacity) > 0n);
  now += 2500n;
  assert.ok(api.nw_api_v1_advance(handle, now, 2500n, sequence++) > 0n);
  assert.deepEqual([info(0), info(1), info(2)], [1, 1, 3]);

  // Agent ports: START is refused mid-run, port 12 clicks, 17 is the last.
  assert.equal(api.nw_desktop_agent_event(handle, 100.0, 17n), 2n);
  assert.equal(api.nw_desktop_agent_event(handle, 100.0, 12n), 1n);
  assert.equal(info(9), 1);
  assert.ok(api.nw_desktop_agent_event(handle, 100.0, 18n) < 0n);
  assert.equal(api.nw_desktop_agent_event(handle, 99.0, 12n), 2n, "time does not run backwards");
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
const environment = createDesktopEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 17);
  assert.ok(environment.act(0).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("PASS: Desktop WASM Computer use tab, options notes, the pointer stepped by arrows, a click, Done under " +
  "par, feedback pause, right click, hold and let go, a slipped mouse click on Done, options and agent controls");
