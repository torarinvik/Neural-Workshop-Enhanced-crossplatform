import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const { exports: api, createWhereWasItEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_where_was_it();
assert.equal(task, 1679726570n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const create = rung => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, 17n);
assert.equal(create(2n), -3n);
const run = create(20n);
assert.ok(run > 0n);
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
let sequence = 0n;
const key = (time, code) => api.nw_api_v1_dispatch(run, 2n, time, sequence++, code, 0n, 0n, 0n, 0n, 0n, 0n);
const click = (time, x, y) => api.nw_api_v1_dispatch(run, 5n, time, sequence++, 0n, 0n, 0n, 0n,
  BigInt(Math.round(x / 912 * 1e6)), BigInt(Math.round(y / 684 * 1e6)), 0n);
const info = field => api.nw_api_v1_where_was_it_info(run, BigInt(field));
const commands = () => {
  const length = api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n);
  assert.ok(length > 0n);
  return decode(new Uint8Array(api.memory.buffer, Number(buffer), Number(length)));
};
const labels = () => commands().filter(command => command.kind === Kind.TEXT).map(command => command.text);
assert.ok(labels().includes("Press Space or click to start"));
assert.equal(key(0n, 1n), 1n);
assert.equal(info(5), 5n);
assert.ok(labels().some(text => text.startsWith("Room 1 of 5:")));
assert.ok(commands().some(command => command.kind === Kind.POLYGON));
assert.equal(click(0n, 400, 400), 2n);
assert.equal(click(0n, 456, 190), 1n);
for (let room = 1; room < 5; room++) assert.equal(key(1n, 2n), 1n);
assert.equal(info(8), -1n);
assert.equal(info(15), -6n);
assert.ok(labels().includes("Something in the bedroom has gone. Click where it stood."));
assert.equal(key(1n, 1n), 2n);
// Python's visible polygon hit at this point lands on the missing thing's square.
assert.equal(click(2n, 436.53438190383775, 451.86774372677917), 1n);
assert.equal(info(8), 7n);
assert.equal(info(9), 1n);
assert.equal(info(1), 21n);
assert.ok(labels().includes("Right: that is where the missing thing stood"));
assert.equal(api.nw_api_v1_advance(run, 3001n, 0n, sequence++), 2n);
assert.equal(api.nw_api_v1_advance(run, 3002n, 0n, sequence++), 1n);
assert.ok(labels().includes("1 of 1 passed   highest rung passed 20"));
assert.ok(labels().includes("Right: that is where the missing thing stood"));
assert.equal(api.nw_api_v1_destroy(run), 0n);
api.nw_frame_free(buffer);

assert.ok(TASK_IDS_BY_CATEGORY[1].includes("where_was_it"));
const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const WHERE_WAS_IT_SETTINGS"), html.indexOf("const SAME_OR_MIRROR_SETTINGS"));
const storage = new Map();
const listeners = new Map();
const note = {};
const form = {
  hidden: true,
  elements: {
    rung: { focus() {}, addEventListener: (event, callback) => listeners.set(event, callback) },
    rounds: {}, adaptive: {},
  },
  addEventListener: (event, callback) => listeners.set(event, callback),
  querySelector: () => ({ addEventListener() {} }),
};
const formBuffer = api.nw_frame_alloc(capacity);
let host;
host = vm.createContext({
  exports: api, framePtr: Number(formBuffer), FRAME_CAPACITY: Number(capacity), TextDecoder,
  view: size => new Uint8Array(api.memory.buffer, Number(formBuffer), size),
  canvas: { width: 912, height: 684, focus() {} }, screen: "taskhub",
  document: { getElementById: id => id === "where-was-it-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "where_was_it",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openWhereWasItOptions(true);
assert.equal(form.elements.rounds.value, 8);
form.elements.rung.value = 20;
form.elements.rounds.value = 1;
listeners.get("change")();
assert.equal(note.textContent, "Rung 20: 5 rooms of 7 things on 6 by 5.  The same things in every room.  " +
  "Seen at the test from 30 to 180 degrees round.");
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.whereWasItInfo(1), 20);
assert.equal(host.whereWasItInfo(3), 1);
host.destroyWhereWasItRun();
api.nw_frame_free(formBuffer);

const canvas = { width: 912, height: 684 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  fillRect() {}, strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {},
  moveTo() {}, lineTo() {}, closePath() {},
  clearRect() { pixels.fill(0); },
  fillText() {
    const colors = {
      "rgba(64,255,64,1.000)": [64, 255, 64, 255],
      "rgba(255,64,64,1.000)": [255, 64, 64, 255],
    };
    const color = colors[this.fillStyle];
    if (color) {
      pixels.set(color, pixels.length - 4);
      pixels.set(color, pixels.length - 4 - canvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};
const environment = createWhereWasItEnvironment(context, { seed: 17, rung: 20, trials: 1 });
assert.equal(environment.n_actions, 31);
for (let room = 0; room < 5; room++) assert.equal(environment.step(30)[0].outcome, undefined);
const verdict = environment.step(7)[0];
assert.equal(verdict.outcome.scalar, 1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.close();

const clock = createWhereWasItEnvironment(context, {
  seed: 17, trials: 2, frameHz: 20, thinkSeconds: 0.1, refillSeconds: 0.05,
});
assert.equal(clock.step()[0].outcome, undefined);
const flag = clock.step()[0];
assert.equal(flag.outcome.scalar, -1);
assert.ok(clock.verify(flag.outcome, flag));
assert.equal(clock.forfeits, 1);
assert.equal(clock.step()[2], false);
assert.equal(clock.think_left, 0.05);
assert.equal(clock.step()[0].outcome.scalar, -1);
assert.equal(clock.step()[2], true);
clock.close();
console.log("PASS: Where Was It? WASM room phases, rotated polygon clicks, outcomes, and think clock");
