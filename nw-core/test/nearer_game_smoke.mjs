import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createWhichIsNearerEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_which_is_nearer();
assert.equal(task, 3493829017n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
assert.ok(TASK_IDS_BY_CATEGORY[3].includes("which_is_nearer"));
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = size => new Uint8Array(api.memory.buffer, Number(buffer), Number(size));
const length = api.nw_which_is_nearer_options_note(buffer, capacity, 20n);
assert.equal(new TextDecoder().decode(view(length)),
  "Rung 20: 3 solids; the cue left is motion parallax as the eye sways.  Nearest over next at least 1.10.  Put them all in order.");
const create = rung => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, 17n);
assert.equal(create(2n), -3n);
const run = create(20n);
assert.ok(run > 0n);
let sequence = 0n;
const key = (now, code) => api.nw_api_v1_dispatch(run, 2n, now, sequence++, code, 0n, 0n, 0n, 0n, 0n, 0n);
const pointer = (now, x, y) => api.nw_api_v1_dispatch(run, 5n, now, sequence++, 0n, 0n, 0n, 0n,
  BigInt(Math.round(x / 912 * 1e6)), BigInt(Math.round(y / 684 * 1e6)), 0n);
const info = field => api.nw_api_v1_which_is_nearer_info(run, BigInt(field));
const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n)));
const labels = commands => commands.filter(command => command.kind === Kind.TEXT).map(command => command.text);
assert.ok(labels(frame()).includes("Press Space or click to start"));
assert.equal(key(0n, 1n), 1n);
const start = frame();
assert.ok(labels(start).includes("Click them in order, nearest first"));
assert.equal(info(4), 4n);
assert.equal(info(5), 3n);
assert.equal(info(14), -6n);
assert.equal(api.nw_api_v1_advance(run, 600n, 600n, sequence++), 1n);
const swung = frame();
assert.notDeepEqual(swung, start);
assert.equal(info(13), 600n);
assert.ok(!labels(swung).some(text => text.startsWith("nearest first:")));
assert.equal(pointer(601n, 456, 205), 1n);
assert.equal(info(8), 1n);
assert.equal(key(602n, 13n), 2n);
assert.equal(key(603n, 12n), 1n);
assert.equal(key(604n, 14n), 1n);
assert.equal(info(0), 2n);
assert.equal(info(1), 21n);
assert.ok(labels(frame()).includes("nearest first: 2 1 3"));
assert.equal(api.nw_api_v1_advance(run, 3603n, 0n, sequence++), 2n);
assert.equal(api.nw_api_v1_advance(run, 3604n, 0n, sequence++), 1n);
assert.ok(labels(frame()).includes("1 of 1 passed   highest rung passed 20"));
assert.equal(api.nw_api_v1_destroy(run), 0n);
api.nw_frame_free(buffer);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const WHICH_IS_NEARER_SETTINGS"), html.indexOf("const STOP_SWITCH_SETTINGS"));
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
  document: { getElementById: id => id === "which-is-nearer-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "which_is_nearer",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openWhichIsNearerOptions(true);
assert.equal(form.elements.rounds.value, 12);
form.elements.rung.value = 20;
form.elements.rounds.value = 1;
listeners.get("change")();
assert.match(note.textContent, /motion parallax.*1.10/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.whichIsNearerInfo(1), 20);
assert.equal(host.whichIsNearerInfo(3), 1);
host.destroyWhichIsNearerRun();
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
const environment = createWhichIsNearerEnvironment(context, { seed: 17, rung: 20, trials: 1 });
assert.equal(environment.n_actions, 6);
assert.equal(environment.step(1)[0].outcome, undefined);
assert.equal(environment.step(0)[0].outcome, undefined);
const verdict = environment.step(2)[0];
assert.equal(verdict.outcome.scalar, 1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.reset(17);
const miss = environment.step(0)[0];
assert.equal(miss.outcome.scalar, -1);
assert.ok(environment.verify(miss.outcome, miss));
environment.close();
assert.throws(() => createWhichIsNearerEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
console.log("PASS: Which Is Nearer? WASM options, sway, clicks, ordered picks, outcomes, and cleanup");
