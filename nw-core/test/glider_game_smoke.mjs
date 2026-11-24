import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createGliderEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_glider();
assert.equal(task, 3159511168n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const attention = TASK_IDS_BY_CATEGORY[2];
assert.equal(attention[attention.indexOf("keep_the_beat") + 1], "glider");
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = size => new Uint8Array(api.memory.buffer, Number(buffer), Number(size));
const noteLength = api.nw_glider_options_note(buffer, capacity, 20n);
assert.equal(new TextDecoder().decode(view(noteLength)), "Rung 20: 10 walls with 17.0 unit gaps, moving gaps, gusts.");
const create = (rung, seed = 17n) => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, seed);
assert.equal(create(2n), -3n);
const run = create(1n);
let now = 0n;
let seq = 0n;
const dispatch = (kind, code, value = 0n) =>
  api.nw_api_v1_dispatch(run, kind, now, seq++, code, value, 0n, 0n, 500000n, 500000n, 0n);
const info = field => api.nw_api_v1_glider_info(run, BigInt(field));
const advance = () => {
  now += 50n;
  return api.nw_api_v1_advance(run, now, 0n, seq++);
};
const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n)));
const label = text => frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes(text));
assert.ok(label("Press Space"));
assert.equal(dispatch(2n, 1n), 1n);
assert.equal(info(5), 30000n);
assert.ok(label("Thread every gap") && label("wall 1 of 6"));
assert.equal(dispatch(2n, 4n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(13), 1n);
assert.ok(info(11) > 0n);
assert.equal(dispatch(3n, 1n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(13), 1n);
assert.equal(dispatch(9n, 0n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(13), 0n);
for (let index = 0; index < 150 && info(0) === 1n; index++) assert.equal(advance(), 1n);
assert.equal(info(0), 2n);
assert.equal(info(7), 2n);
assert.ok(label("Hit the canyon floor"));
const deadline = info(10);
assert.equal(api.nw_api_v1_advance(run, deadline - 1n, 0n, seq++), 2n);
assert.equal(api.nw_api_v1_advance(run, deadline, 0n, seq++), 1n);
assert.equal(info(0), 3n);
assert.equal(api.nw_api_v1_destroy(run), 0n);

const pulse = create(7n);
assert.equal(api.nw_glider_agent_event(pulse, 0, 1n), 1n);
assert.equal(api.nw_glider_agent_event(pulse, 0, 0n), 1n);
assert.equal(api.nw_glider_agent_event(pulse, 0.050, -1n), 1n);
assert.equal(api.nw_api_v1_glider_info(pulse, 13n), 1n);
assert.ok(api.nw_api_v1_glider_info(pulse, 11n) > 0n);
assert.equal(api.nw_glider_agent_event(pulse, 0.100, -1n), 1n);
assert.equal(api.nw_api_v1_glider_info(pulse, 13n), 0n);
assert.equal(api.nw_api_v1_destroy(pulse), 0n);
api.nw_frame_free(buffer);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const GLIDER_SETTINGS"), html.indexOf("const NOTEBOOK_SETTINGS"));
const storage = new Map();
const listeners = new Map();
const note = {};
const form = {
  hidden: true,
  elements: {
    rung: { focus() {}, addEventListener: (event, callback) => listeners.set(event, callback) },
    flights: {}, adaptive: {},
  },
  addEventListener: (event, callback) => listeners.set(event, callback),
  querySelector: () => ({ addEventListener() {} }),
};
const formBuffer = api.nw_frame_alloc(capacity);
const controls = [];
let host;
host = vm.createContext({
  exports: api, framePtr: Number(formBuffer), FRAME_CAPACITY: Number(capacity), TextDecoder,
  view: size => new Uint8Array(api.memory.buffer, Number(formBuffer), size),
  canvas: { width: 912, height: 684, focus() {} }, screen: "taskhub",
  document: { getElementById: id => id === "glider-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "glider",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  apiDispatchAction: (_handle, action) => { controls.push(action); return 2n; },
  apiDispatchLifecycle: (_handle, kind, value) => controls.push([kind, value]),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openGliderOptions(true);
assert.equal(form.elements.flights.value, 5);
form.elements.rung.value = 25;
form.elements.flights.value = 1;
listeners.get("change")();
assert.match(note.textContent, /10 walls.*moving gaps, gusts/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.gliderInfo(1), 25);
assert.equal(host.gliderInfo(3), 1);
for (const [key, down] of [["w", true], ["ArrowUp", true], ["w", false], ["ArrowUp", false],
  [" ", true], [" ", false]]) {
  assert.ok(host.gliderControl({ key, preventDefault() {} }, down));
}
host.clearGliderControls(9n);
assert.deepEqual(controls, [0, 0, 0, 2, 1, 0, 2, [9n, 0]]);
host.destroyGliderRun();
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
const environment = createGliderEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 40 });
assert.equal(environment.n_actions, 1);
let verdict;
for (let i = 0; i < 420 && !verdict; i++) {
  const [observation] = environment.step();
  if (observation.outcome) verdict = observation;
}
assert.equal(verdict.outcome.scalar, -1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.close();
assert.throws(() => createGliderEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
console.log("PASS: Glider WASM held controls, focus cleanup, canyon rendering, options, one-frame agent controls, and verdict");
