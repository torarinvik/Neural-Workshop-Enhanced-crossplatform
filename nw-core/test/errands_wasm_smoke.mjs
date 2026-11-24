import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createErrandsEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_errands();
assert.equal(task, 1095090106n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.deepEqual(TASK_IDS_BY_CATEGORY[8].slice(0, 6), ["desktop", "forms", "manual", "browser", "errands", "spreadsheet"]);

const EVENT = { keyDown: 2n, pointerDown: 5n, wheel: 7n };
const KEY_CODE = { space: 1, enter: 2, up: 4, down: 6, backspace: 25 };
const DIGIT_CODES = [22, 12, 13, 14, 15, 16, 17, 18, 19, 21];
// Where the 1000 by 640 page sits in the 912 by 684 window, y up.
const LEFT = 152.09375;
const TOP = 568;
const SCALE = 0.6078125;
const STRIP = 40;
const TABS = { mail: [10, 5, 130, 30], expenses: [290, 5, 150, 30] };
const DONE = [880, 5, 110, 30];
const FIELDS = { order: [200, STRIP + 70, 260, 40], amount: [200, STRIP + 130, 260, 40] };
const SUBMIT = [40, STRIP + 470, 220, 50];
const handle = api.nw_api_v1_create(task, 1n, 1n, 3n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => Number(api.nw_api_v1_errands_info(handle, BigInt(field)));
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
function pressBox([x, y, w, h]) {
  return press(LEFT + (x + w / 2) * SCALE, TOP - (y + h / 2) * SCALE);
}
// A press on the first drawn text that matches.
function pressText(match) {
  const found = commands().find(command => command.text === match);
  assert.ok(found, `${match}: ${texts().join(" | ")}`);
  return press(found.a, found.b);
}
function note(rung) {
  return new TextDecoder().decode(view(api.nw_errands_options_note(pointer, capacity, BigInt(rung))));
}
function typeNumber(value) {
  for (const digit of String(value)) assert.equal(key(DIGIT_CODES[Number(digit)]), 1n);
}
function found(pattern) {
  const line = texts().find(text => pattern.test(text));
  assert.ok(line, `${pattern}: ${texts().join(" | ")}`);
  return line.match(pattern);
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 8n, 0n, 0n, 912n, 684n)));
  for (const name of ["Browser", "Errands", "Spreadsheet"]) assert.ok(menu.some(command => command.text === name), name);
  assert.equal(note(1), "Rung 1: 1 errand, 0 other mails.  With a receipt to claim, no shopping.  Par allows 100% of " +
    "a thorough worker's extra clicks.");
  assert.equal(note(30), "Rung 30: 3 errands, 6 other mails.  With categories from a policy mail, a request changed " +
    "by a later mail.  Par allows 5% of a thorough worker's extra clicks.");
  assert.ok(api.nw_errands_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");

  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(key(DIGIT_CODES[4]), 2n, "digits do nothing before the run");
  assert.equal(key(KEY_CODE.space), 1n);
  assert.deepEqual([info(0), info(2), info(3), info(9), info(11)], [1, 1, 3, 0, 0]);
  assert.ok(texts().includes("Do what the mail asks, then press Done"));
  assert.ok(texts().includes("Inbox") && texts().includes("Receipt to claim"));
  assert.equal(key(DIGIT_CODES[4]), 2n, "digits only type in Expenses");

  // Open the receipt and read what to claim.
  assert.equal(pressText("Receipt to claim"), 1n);
  assert.ok(texts().includes("< Inbox"));
  const order = found(/^Order #(\d+)$/)[1];
  const amount = found(/^Total charged: \$(\d+)$/)[1];
  const category = texts().join(" ").match(/ under (\w+)\?/)[1];
  assert.equal(info(9), 1);

  // Expenses: the keyboard types into the focused field, each a click.
  assert.equal(pressBox(TABS.expenses), 1n);
  assert.equal(info(11), 2);
  assert.equal(pressBox(SUBMIT), 1n);
  assert.ok(texts().includes("Fill in every part of the claim first."));
  assert.equal(key(DIGIT_CODES[7]), 1n);
  assert.ok(texts().includes("7|"));
  assert.equal(key(KEY_CODE.backspace, 1n), 2n, "a repeated Backspace is ignored");
  assert.equal(key(KEY_CODE.backspace), 1n);
  assert.equal(key(KEY_CODE.enter), 2n, "Enter does nothing");
  typeNumber(order);
  assert.equal(pressBox(FIELDS.amount), 1n);
  typeNumber(amount);
  assert.equal(pressText(`( ) ${category}`), 1n);
  assert.ok(texts().includes(`(o) ${category}`));
  assert.equal(pressBox(SUBMIT), 1n);
  assert.ok(texts().includes("Claim filed.") && texts().includes(`#${order}  $${amount}  ${category}`));
  assert.equal(info(12), 1);

  // Scrolling outside the shop changes nothing and is not a click.
  const clicks = info(9);
  assert.equal(key(KEY_CODE.down), 1n);
  assert.equal(dispatch(EVENT.wheel, 0, 0n), 2n);
  assert.equal(info(9), clicks);

  // Done: judged against par.
  assert.equal(pressBox(DONE), 1n);
  const [phase, verdict, total, par] = [info(0), info(8), info(9), info(10)];
  assert.deepEqual([phase, total], [2, clicks + 1]);
  assert.ok([1, 2].includes(verdict) && (verdict === 1) === (total <= par), String([verdict, total, par]));
  const words = verdict === 1 ? `All done in ${total} clicks (par ${par})`
    : `All done, but ${total} clicks against a par of ${par}`;
  assert.ok(texts().includes(words), texts().join(" | "));
  assert.equal(pressBox(TABS.mail), 2n, "no clicks while judged");
  assert.equal(api.nw_errands_options_apply(handle, 3n, 1n, 0n), 2n, "no options mid-run");

  // The verdict holds for 2.5 seconds, then the next day.
  now += 2000n;
  assert.ok(api.nw_api_v1_advance(handle, now, 2000n, sequence++) > 0n);
  assert.equal(info(0), 2);
  now += 600n;
  assert.ok(api.nw_api_v1_advance(handle, now, 600n, sequence++) > 0n);
  assert.deepEqual([info(0), info(1), info(2), info(9), info(12)], [1, verdict === 1 ? 2 : 1, 2, 0, 0]);

  // Done with nothing done.
  assert.equal(pressBox(DONE), 1n);
  assert.deepEqual([info(0), info(8)], [2, 3]);
  assert.ok(texts().some(text => text.startsWith("Not done: ")), texts().join(" | "));
  assert.ok(api.nw_api_v1_read_state(handle, pointer, capacity) > 0n);

  // Agent ports: START is refused mid-run, a frame steps past the verdict,
  // then a pointer move.
  assert.equal(api.nw_errands_agent_event(handle, 10.0, 15n), 2n);
  assert.equal(api.nw_errands_agent_event(handle, 10.0, -1n), 1n);
  assert.deepEqual([info(0), info(2)], [1, 3]);
  const spot = [info(13), info(14)];
  assert.equal(api.nw_errands_agent_event(handle, 10.0, 0n), 1n);
  assert.notDeepEqual([info(13), info(14)], spot, "port 0 moves the pointer");
  assert.ok(api.nw_errands_agent_event(handle, 10.0, 16n) < 0n);
  assert.equal(api.nw_errands_agent_event(handle, 9.0, 0n), 2n, "time does not run backwards");
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
const environment = createErrandsEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 15);
  assert.ok(environment.act(12).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("PASS: Errands WASM Computer use tab, options notes, reading a mail, filing a claim from the keyboard, " +
  "verdicts against par, feedback pause, options and agent controls");
