import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createFormsEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_forms();
assert.equal(task, 2143393500n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.deepEqual(TASK_IDS_BY_CATEGORY[8].slice(0, 6), ["desktop", "forms", "manual", "browser", "errands", "spreadsheet"]);

const EVENT = { keyDown: 2n, pointerDown: 5n, text: 8n };
const KEY_CODE = { space: 1, enter: 2, up: 4, down: 6, tab: 23, backspace: 25 };
const handle = api.nw_api_v1_create(task, 1n, 1n, 3n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => Number(api.nw_api_v1_forms_info(handle, BigInt(field)));
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
function dispatch(kind, code = 0, x = 0n, y = 0n, flags = 0n, value = 0n) {
  now += 50n;
  return api.nw_api_v1_dispatch(handle, kind, now, sequence++, BigInt(code), value, 0n, flags, x, y, 0n);
}
function key(code, flags = 0n) {
  return dispatch(EVENT.keyDown, code, 0n, 0n, flags);
}
function type(words) {
  return [...words].map(character => dispatch(EVENT.text, 0, 0n, 0n, 0n, BigInt(character.codePointAt(0))));
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
function note(rung) {
  return new TextDecoder().decode(view(api.nw_forms_options_note(pointer, capacity, BigInt(rung))));
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 8n, 0n, 0n, 912n, 684n)));
  for (const name of ["Forms", "Manual", "Browser", "Errands", "Spreadsheet"]) assert.ok(menu.some(command => command.text === name), name);
  assert.equal(note(1), "Rung 1: up to 1 fields on 1 page(s).");
  assert.equal(note(25), "Rung 25: up to 12 fields on 3 page(s).  With dates to reformat, phone numbers, lists that " +
    "complete, checkboxes and radio buttons, fields that appear, a letter to read, other people's details.  Par is the " +
    "reference typist exactly.");
  assert.ok(api.nw_forms_options_note(pointer, capacity, 3n) < 0n, "rung 3 is not offered");

  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(key(KEY_CODE.enter), 2n, "Enter does nothing before the run");
  assert.deepEqual(type("R"), [2n], "nothing is typed before the run");
  assert.equal(key(KEY_CODE.space), 1n);
  assert.deepEqual([info(0), info(1), info(2), info(3), info(9), info(12)], [1, 1, 1, 3, 0, 0]);
  for (const words of ["Forms", "Fill in the form in 10.4 keys or fewer", "The card", "Name: Rex Rossi", "First name", "|",
    "rung 1  1/3  keys 0  a page sent back costs 5"]) assert.ok(texts().includes(words), words);

  // Characters arrive as text; Space during a form is a character, not a key.
  assert.deepEqual(type("Rex"), [1n, 1n, 1n]);
  assert.equal(key(KEY_CODE.space), 2n, "Space as a key does nothing while filling");
  assert.ok(texts().includes("Rex|"));
  assert.equal(info(9), 3);
  assert.deepEqual(type("~"), [2n], "a character forms.py does not take");
  assert.equal(key(KEY_CODE.enter, 1n), 2n, "a repeated Enter is ignored");
  assert.equal(key(KEY_CODE.enter), 1n);
  assert.deepEqual([info(0), info(8), info(4), info(1)], [2, 1, 1, 2]);
  assert.ok(texts().includes("All right in 4 keys against a par of 10.4"));
  assert.deepEqual(type("x"), [2n], "no typing while judged");
  assert.equal(api.nw_forms_options_apply(handle, 1n, 1n, 0n), 2n, "no options mid-run");

  // The verdict holds for three seconds, then the next form at rung 2.
  now += 2500n;
  assert.ok(api.nw_api_v1_advance(handle, now, 2500n, sequence++) > 0n);
  assert.equal(info(0), 2);
  now += 600n;
  assert.ok(api.nw_api_v1_advance(handle, now, 600n, sequence++) > 0n);
  assert.deepEqual([info(0), info(1), info(2), info(9)], [1, 2, 2, 0]);

  // A click on Last name's row moves the focus there, for a key.
  const last = label("Last name");
  assert.equal(press(last.a + 300, last.b), 1n);
  assert.deepEqual([info(12), info(9)], [1, 1]);
  assert.equal(press(5, 5), 2n, "a press on nothing does nothing");
  assert.equal(key(KEY_CODE.backspace), 1n);
  assert.equal(key(KEY_CODE.tab), 1n);
  assert.deepEqual([info(12), info(9)], [0, 3]);
  // Sent empty: the page comes back, marked, at the rung's penalty.
  assert.equal(key(KEY_CODE.enter), 1n);
  assert.deepEqual([info(0), info(10), info(13)], [1, 1, 10]);
  assert.ok(texts().includes("rung 2  2/3  keys 4  a page sent back costs 6  sent back 1"), texts().join(" | "));
  assert.ok(api.nw_api_v1_read_state(handle, pointer, capacity) > 0n);

  // Agent ports: START is refused mid-run, port 0 is the letter a.
  assert.equal(api.nw_forms_agent_event(handle, 10.0, 46n), 2n);
  assert.equal(api.nw_forms_agent_event(handle, 10.0, 0n), 1n);
  assert.equal(info(9), 5);
  assert.ok(texts().includes("a|"));
  assert.ok(api.nw_forms_agent_event(handle, 10.0, 47n) < 0n);
  assert.equal(api.nw_forms_agent_event(handle, 9.0, 0n), 2n, "time does not run backwards");
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
const environment = createFormsEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 46);
  assert.ok(environment.act(0).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("PASS: Forms WASM Computer use tab, options notes, typing as text, named keys, a click to focus, a page sent " +
  "back, right answers against par, feedback pause, options and agent controls");
