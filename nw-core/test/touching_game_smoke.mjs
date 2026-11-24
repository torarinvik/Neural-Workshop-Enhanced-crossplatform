import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createTouchingEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_touching();
assert.equal(task, 4278212208n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.equal(TASK_IDS_BY_CATEGORY[3].includes("touching"), true);
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = size => new Uint8Array(api.memory.buffer, Number(buffer), Number(size));
const noteLength = api.nw_touching_options_note(buffer, capacity, 20n);
assert.equal(new TextDecoder().decode(view(noteLength)), "Rung 20.  Count the touching pairs among 5 shapes.  Squares too.");
const create = rung => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, 17n);
assert.equal(create(2n), -3n);
let run = create(1n);
let sequence = 0n;
const key = (now, code) => api.nw_api_v1_dispatch(run, 2n, now, sequence++, code, 0n, 0n, 0n, 0n, 0n, 0n);
const pointer = (now, x, y) => api.nw_api_v1_dispatch(run, 5n, now, sequence++, 0n, 0n, 0n, 0n,
  BigInt(Math.round(x / 912 * 1e6)), BigInt(Math.round(y / 684 * 1e6)), 0n);
const info = field => api.nw_api_v1_touching_info(run, BigInt(field));
const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n)));
const labels = commands => commands.filter(command => command.kind === Kind.TEXT).map(command => command.text);
assert.ok(labels(frame()).includes("Press Space or click to start"));
assert.equal(key(0n, 1n), 1n);
assert.equal(info(4), 3n);
assert.equal(info(5), 2n);
assert.equal(info(6), 0n);
assert.equal(info(8), -1n);
assert.ok(labels(frame()).includes("Do the two shapes touch?"));
assert.ok(frame().some(command => command.kind === Kind.LINE));
assert.equal(pointer(1n, 456, 370), 2n);
assert.equal(pointer(2n, 745, 200), 1n);
assert.equal(info(7), 2n);
assert.equal(info(8), 1n);
assert.equal(info(1), 2n);
assert.ok(labels(frame()).includes("Right: Overlapping"));
assert.equal(api.nw_api_v1_advance(run, 2501n, 0n, sequence++), 2n);
assert.equal(api.nw_api_v1_advance(run, 2502n, 0n, sequence++), 1n);
assert.ok(labels(frame()).includes("1 of 1 passed   highest rung passed 1"));
assert.equal(api.nw_api_v1_destroy(run), 0n);

run = create(10n);
sequence = 0n;
assert.equal(pointer(0n, 456, 410), 1n);
assert.equal(info(4), 6n);
assert.equal(info(5), 3n);
assert.ok(labels(frame()).includes("How many pairs of shapes touch (just touch, not overlap)?"));
assert.equal(key(1n, 17n), 2n);
assert.equal(key(2n, 22n), 1n);
assert.equal(info(8), 1n);
assert.equal(api.nw_api_v1_destroy(run), 0n);
api.nw_frame_free(buffer);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const TOUCHING_SETTINGS"), html.indexOf("const CROSSINGS_SETTINGS"));
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
  document: { getElementById: id => id === "touching-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "touching",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openTouchingOptions(true);
assert.equal(form.elements.rounds.value, 5);
form.elements.rung.value = 25;
form.elements.rounds.value = 1;
listeners.get("change")();
assert.match(note.textContent, /6 shapes.*Squares too/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.touchingInfo(1), 25);
assert.equal(host.touchingInfo(3), 1);
host.destroyTouchingRun();
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
const environment = createTouchingEnvironment(context, { seed: 17, rung: 25, trials: 1 });
assert.equal(environment.n_actions, 6);
const verdict = environment.step(1)[0];
assert.equal(verdict.outcome.scalar, 1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.close();

const clock = createTouchingEnvironment(context, {
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
console.log("PASS: Touching? WASM shape relations and touching-pair counts, pointer and key answers, settings, think clock, and outcomes");
