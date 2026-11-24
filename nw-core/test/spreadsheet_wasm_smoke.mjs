import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createSpreadsheetEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_spreadsheet();
assert.equal(task, 36128217n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(TASK_IDS_BY_CATEGORY[8][5], "spreadsheet");

const EVENT = { keyDown: 2n, pointerDown: 5n, wheel: 7n };
const KEY_CODE = { space: 1, enter: 2, up: 4, down: 6, backspace: 25 };
const DIGIT_CODES = [22, 12, 13, 14, 15, 16, 17, 18, 19, 21];
// Where the 1000 by 640 page sits in the 912 by 684 window, y up.
const LEFT = 152.09375;
const TOP = 568;
const SCALE = 0.6078125;
const handle = api.nw_api_v1_create(task, 1n, 1n, 3n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => Number(api.nw_api_v1_spreadsheet_info(handle, BigInt(field)));
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
function dispatch(kind, code = 0, value = 0n, x = 0n, y = 0n, flags = 0n) {
  now += 50n;
  return api.nw_api_v1_dispatch(handle, kind, now, sequence++, BigInt(code), value, 0n, flags, x, y, 0n);
}
function key(code, flags = 0n) {
  return dispatch(EVENT.keyDown, code, 0n, 0n, 0n, flags);
}
// A press at a window point, y up, in reference units.
function press(x, y) {
  return dispatch(EVENT.pointerDown, 0, 0n, BigInt(Math.round(x * 1000000 / 912)), BigInt(Math.round(y * 1000000 / 684)));
}
function pressPage(x, y) {
  return press(LEFT + x * SCALE, TOP - y * SCALE);
}
// A press on the first drawn text that matches.
function pressText(match) {
  const test = typeof match === "string" ? text => text === match : match;
  const found = commands().find(command => command.text && test(command.text));
  assert.ok(found, `${match}: ${texts().join(" | ")}`);
  return press(found.a, found.b);
}
function note(rung) {
  return new TextDecoder().decode(view(api.nw_spreadsheet_options_note(pointer, capacity, BigInt(rung))));
}

function typeNumber(value) {
  for (const digit of String(value)) assert.equal(key(DIGIT_CODES[Number(digit)]), 1n);
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 8n, 0n, 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Browser"));
  assert.ok(menu.some(command => command.text === "Spreadsheet"));
  assert.equal(note(1), "Rung 1: 8 rows; look up.  Par allows 80% of the reference's clicks for slips, at least three.");
  assert.equal(note(30), "Rung 30: 60 rows; sum a category, count over a bar, find the wrong total, correct the wrong " +
    "total.  Par allows 20% of the reference's clicks for slips, at least three.");
  assert.ok(api.nw_spreadsheet_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");

  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(key(KEY_CODE.backspace), 2n, "Backspace does nothing before the run");
  assert.equal(key(KEY_CODE.space), 1n);
  assert.deepEqual([info(0), info(2), info(3), info(9)], [1, 1, 3, 0]);
  assert.ok(texts().includes("Spreadsheet"));
  assert.ok(texts().some(text => text.startsWith("rung 1  1/3   clicks 0   par ")));
  const question = texts().find(text => text.startsWith("What is the Total for the "));
  assert.ok(question, texts().join(" | "));

  // A click on the Qty header sorts by it; a second turns the sort round.
  assert.equal(pressPage(495, 70), 1n);
  assert.ok(texts().includes("Qty  ^"));
  assert.equal(pressPage(495, 70), 1n);
  assert.ok(texts().includes("Qty  v"));
  assert.equal(info(9), 2);
  // The Total's Sum button fills the status bar.
  assert.equal(pressPage(710, 500), 1n);
  assert.ok(texts().some(text => /^Total of visible rows:  sum \d+   count 8   largest \d+$/.test(text)));
  assert.equal(info(9), 3);

  // Keys type into the answer box, each a click; repeats are ignored.
  assert.equal(key(DIGIT_CODES[7]), 1n);
  assert.deepEqual([info(11), info(12), info(9)], [7, 1, 4]);
  assert.ok(texts().includes("7|"));
  assert.equal(key(KEY_CODE.backspace, 1n), 2n, "a repeated Backspace is ignored");
  assert.equal(key(KEY_CODE.backspace), 1n);
  assert.equal(key(KEY_CODE.enter), 1n, "Enter with nothing typed is a click and nothing more");
  assert.deepEqual([info(0), info(12), info(9)], [1, 0, 6]);

  // Scrolling is not a click.
  assert.equal(key(KEY_CODE.down), 1n);
  assert.equal(key(KEY_CODE.up), 1n);
  assert.equal(dispatch(EVENT.wheel, 0, 120000n), 1n);
  assert.equal(dispatch(EVENT.wheel, 0, 0n), 2n);
  assert.equal(info(9), 6);

  // Answer: the asked-for row's Total, read off the sheet, typed, Enter.
  const item = question.slice("What is the Total for the ".length, -1);
  const drawn = texts();
  const at = drawn.indexOf(item);
  assert.ok(at > 0, `${item}: ${drawn.join(" | ")}`);
  const total = Number(drawn[at + 4]);
  typeNumber(total);
  assert.equal(key(KEY_CODE.enter), 1n);
  const [phase, verdict, clicks, par] = [info(0), info(8), info(9), info(10)];
  assert.deepEqual([phase, clicks], [2, 7 + String(total).length]);
  const words = verdict === 1 ? `Right: ${total}, in ${clicks} clicks (par ${par})`
    : `Right, but ${clicks} clicks against a par of ${par}`;
  assert.ok([1, 2].includes(verdict) && (verdict === 1) === (clicks <= par));
  assert.ok(texts().includes(words), texts().join(" | "));
  assert.equal(pressPage(495, 70), 2n, "no clicks while judged");
  assert.equal(key(DIGIT_CODES[1]), 2n, "no typing while judged");
  assert.equal(api.nw_spreadsheet_options_apply(handle, 4n, 1n, 0n), 2n, "no options mid-run");

  // The verdict holds for 2.5 seconds, then the next question.
  now += 2000n;
  assert.ok(api.nw_api_v1_advance(handle, now, 2000n, sequence++) > 0n);
  assert.equal(info(0), 2);
  now += 600n;
  assert.ok(api.nw_api_v1_advance(handle, now, 600n, sequence++) > 0n);
  assert.deepEqual([info(0), info(1), info(2), info(9), info(12)], [1, verdict === 1 ? 2 : 1, 2, 0, 0]);

  // A wrong answer.
  typeNumber(1000000);
  assert.equal(key(KEY_CODE.enter), 1n);
  assert.deepEqual([info(0), info(8)], [2, 3]);
  assert.ok(texts().some(text => /^No: the answer was \d+$/.test(text)), texts().join(" | "));
  const state = api.nw_api_v1_read_state(handle, pointer, capacity);
  assert.ok(state > 0n);

  // Agent ports: START is refused mid-run, a frame steps past the verdict,
  // then a pointer move.
  assert.equal(api.nw_spreadsheet_agent_event(handle, 10.0, 15n), 2n);
  assert.equal(api.nw_spreadsheet_agent_event(handle, 10.0, -1n), 1n);
  assert.deepEqual([info(0), info(2)], [1, 3]);
  assert.equal(api.nw_spreadsheet_agent_event(handle, 10.0, 0n), 1n);
  assert.ok(api.nw_spreadsheet_agent_event(handle, 10.0, 16n) < 0n);
  assert.equal(api.nw_spreadsheet_agent_event(handle, 9.0, 0n), 2n, "time does not run backwards");
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
const environment = createSpreadsheetEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 15);
  assert.ok(environment.act(12).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("PASS: Spreadsheet WASM Computer use tab, options notes, sorting, sums, the keypad from the keyboard, " +
  "scrolling, right and wrong answers, feedback pause, options and agent controls");
