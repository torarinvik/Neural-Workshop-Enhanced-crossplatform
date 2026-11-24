import assert from "node:assert/strict";
import fs from "node:fs";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports: api, createBrowserEnvironment } = await instantiateElisa(artifact, { warn: false });
const task = api.nw_api_v1_task_browser();
assert.equal(task, 122887567n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(TASK_IDS_BY_CATEGORY[8][3], "browser");

const EVENT = { keyDown: 2n, pointerDown: 5n, wheel: 7n };
const DEPARTMENTS = ["Kettles", "Lamps", "Chairs", "Backpacks", "Headphones", "Tents", "Blenders", "Desks"];
const KEY_CODE = { space: 1, up: 4, down: 6, backspace: 25 };
// Where the 1000 by 640 page sits in the 912 by 684 window, y up.
const LEFT = 152.09375;
const TOP = 568;
const SCALE = 0.6078125;
const handle = api.nw_api_v1_create(task, 1n, 1n, 3n, 1n, 0n, 0n, 0n, 17n);
assert.ok(handle > 0n);
const capacity = 1048576n;
const pointer = api.nw_frame_alloc(capacity);
const info = field => Number(api.nw_api_v1_browser_info(handle, BigInt(field)));
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
  return new TextDecoder().decode(view(api.nw_browser_options_note(pointer, capacity, BigInt(rung))));
}

try {
  const menu = decode(view(api.nw_taskhub_write(pointer, capacity, 8n, 0n, 0n, 912n, 684n)));
  assert.ok(menu.some(command => command.text === "Browser"));
  assert.ok(!menu.some(command => command.text === "No tasks in this category yet."));
  assert.equal(note(1), "Rung 1: 1 departments of 2 products; 1 to buy.  " +
    "Par allows 100% of a thorough shopper's extra clicks.");
  assert.equal(note(30), "Rung 30: 5 departments of 24 products; 3 to buy.  With sortable lists, " +
    "stock shown only on product pages, shipping costs, lists over several pages, list prices that may be " +
    "out of date.  Par allows 5% of a thorough shopper's extra clicks.");
  assert.ok(api.nw_browser_options_note(pointer, capacity, 2n) < 0n, "rung 2 is not offered");

  assert.ok(texts().includes("Press Space or click to start"));
  assert.equal(key(KEY_CODE.backspace), 2n, "Backspace does nothing before the run");
  assert.equal(key(KEY_CODE.space), 1n);
  assert.deepEqual([info(0), info(2), info(3), info(9)], [1, 1, 3, 0]);
  assert.ok(texts().includes("Browser"));
  assert.ok(texts().some(text => text.startsWith("rung 1  1/3   clicks 0   par ")));

  // The toolbar's Cart button opens the cart, and Backspace comes back.
  const home = info(11);
  assert.equal(pressPage(935, 53), 1n);
  assert.notEqual(info(11), home);
  assert.equal(info(9), 1);
  assert.ok(texts().includes("The cart is empty."));
  assert.equal(key(KEY_CODE.backspace, 1n), 2n, "a repeated Backspace is ignored");
  assert.equal(key(KEY_CODE.backspace), 1n);
  assert.equal(info(11), home);
  assert.equal(info(9), 2);

  // Scrolling is not a click.
  assert.equal(key(KEY_CODE.down), 1n);
  assert.equal(key(KEY_CODE.up), 1n);
  assert.equal(dispatch(EVENT.wheel, 0, 120000n), 1n);
  assert.equal(dispatch(EVENT.wheel, 0, 0n), 2n);
  assert.equal(info(9), 2);

  // An empty cart does not check out.
  assert.equal(pressPage(935, 53), 1n);
  assert.equal(pressText("Check out"), 1n);
  assert.deepEqual([info(0), info(9)], [1, 4]);
  assert.equal(key(KEY_CODE.backspace), 1n);

  // Shop: the department, its first product, Add to cart, the cart, Check out.
  assert.equal(pressText(text => DEPARTMENTS.includes(text)), 1n);
  assert.equal(pressText(text => /^[A-Z][a-z]+ [A-Z]\d+$/.test(text)), 1n);
  assert.equal(pressText("Add to cart"), 1n);
  assert.equal(info(12), 1);
  assert.equal(pressPage(935, 53), 1n);
  assert.equal(pressText("Check out"), 1n);
  const [phase, verdict, clicks, par] = [info(0), info(8), info(9), info(10)];
  assert.deepEqual([phase, clicks], [2, 10]);
  const words = verdict === 1 ? `Bought the right things in ${clicks} clicks (par ${par})`
    : verdict === 2 ? `The right things, but ${clicks} clicks against a par of ${par}`
      : `Not what the list asked for (${clicks} clicks, par ${par})`;
  assert.ok([1, 2, 3].includes(verdict) && (verdict === 1) === (clicks <= par && verdict !== 3));
  assert.ok(texts().includes(words), texts().join(" | "));
  assert.equal(pressPage(935, 53), 2n, "no clicks while judged");
  assert.equal(api.nw_browser_options_apply(handle, 3n, 1n, 0n), 2n, "no options mid-run");

  // The verdict holds for 2.5 seconds, then the next trip, a rung up on a
  // pass and never below 1.
  now += 2000n;
  assert.ok(api.nw_api_v1_advance(handle, now, 2000n, sequence++) > 0n);
  assert.equal(info(0), 2);
  now += 600n;
  assert.ok(api.nw_api_v1_advance(handle, now, 600n, sequence++) > 0n);
  assert.deepEqual([info(0), info(1), info(2), info(9), info(12)], [1, verdict === 1 ? 2 : 1, 2, 0, 0]);
  const state = api.nw_api_v1_read_state(handle, pointer, capacity);
  assert.ok(state > 0n);

  // Agent ports: a pointer move, then START is refused mid-run.
  assert.equal(api.nw_browser_agent_event(handle, 10.0, 0n), 1n);
  assert.equal(api.nw_browser_agent_event(handle, 10.0, 15n), 2n);
  assert.ok(api.nw_browser_agent_event(handle, 10.0, 16n) < 0n);
  assert.equal(api.nw_browser_agent_event(handle, 9.0, 0n), 2n, "time does not run backwards");
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
const environment = createBrowserEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 20 });
try {
  assert.equal(environment.n_actions, 15);
  assert.ok(environment.act(12).ok);
  assert.equal(environment.advance().done, false);
} finally {
  environment.close();
}
console.log("PASS: Browser WASM Computer use tab, options notes, toolbar and page clicks, Back, scrolling, " +
  "a shopping trip to its verdict, feedback pause, options and agent controls");
