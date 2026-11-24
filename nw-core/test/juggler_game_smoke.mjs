import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createJugglerEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_juggler();
assert.equal(task, 178836257n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const attention = TASK_IDS_BY_CATEGORY[2];
assert.equal(attention[attention.indexOf("lander") + 1], "juggler");
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = size => new Uint8Array(api.memory.buffer, Number(buffer), Number(size));
const noteLength = api.nw_juggler_options_note(buffer, capacity, 20n);
assert.equal(new TextDecoder().decode(view(noteLength)), "Rung 20: 5 ball(s) for 40 s, a 3.8 m tray.  Heavy and light balls.  A draught.");
const create = (rung, seed = 17n) => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, seed);
assert.equal(create(2n), -3n);
const run = create(1n);
let now = 0n;
let seq = 0n;
const dispatch = (kind, code, value = 0n) =>
  api.nw_api_v1_dispatch(run, kind, now, seq++, code, value, 0n, 0n, 500000n, 500000n, 0n);
const info = field => api.nw_api_v1_juggler_info(run, BigInt(field));
const advance = () => {
  now += 25n;
  return api.nw_api_v1_advance(run, now, 0n, seq++);
};
const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n)));
const label = text => frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes(text));
assert.ok(label("Press Space"));
assert.equal(dispatch(5n, 0n), 1n);
assert.equal(info(5), 16000n);
assert.equal(info(12), 1n);
assert.ok(label("Keep every ball"));
assert.equal(dispatch(2n, 5n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(6), 1750n);
assert.ok(info(5) > 16000n);
assert.equal(dispatch(2n, 3n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(6), 0n);
assert.equal(dispatch(3n, 3n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(6), 1750n);
assert.equal(dispatch(9n, 0n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(6), 250n);
for (let i = 0; i < 180 && info(0) === 1n; i++) assert.equal(advance(), 1n);
assert.equal(info(0), 2n);
assert.equal(info(7), 2n);
assert.ok(label("A ball hit the floor"));
const deadline = info(10);
assert.equal(api.nw_api_v1_advance(run, deadline - 1n, 0n, seq++), 2n);
assert.equal(api.nw_api_v1_advance(run, deadline, 0n, seq++), 1n);
assert.equal(info(0), 3n);
assert.equal(api.nw_api_v1_destroy(run), 0n);

const pulse = create(1n);
assert.equal(api.nw_juggler_agent_event(pulse, 0, 2n), 1n);
assert.equal(api.nw_juggler_agent_event(pulse, 0, 0n), 1n);
assert.equal(api.nw_juggler_agent_event(pulse, 0.025, -1n), 1n);
assert.equal(api.nw_api_v1_juggler_info(pulse, 6n), -1750n);
assert.equal(api.nw_juggler_agent_event(pulse, 0.050, -1n), 1n);
assert.equal(api.nw_api_v1_juggler_info(pulse, 6n), -250n);
assert.equal(api.nw_api_v1_destroy(pulse), 0n);
api.nw_frame_free(buffer);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const JUGGLER_SETTINGS"), html.indexOf("const LANDER_SETTINGS"));
const storage = new Map();
const listeners = new Map();
const note = {};
const form = {
  hidden: true,
  elements: {
    rung: { focus() {}, addEventListener: (event, callback) => listeners.set(event, callback) },
    acts: {}, adaptive: {},
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
  document: { getElementById: id => id === "juggler-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "juggler",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  apiDispatchAction: (_handle, action) => { controls.push(action); return 2n; },
  apiDispatchLifecycle: (_handle, kind, value) => controls.push([kind, value]),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openJugglerOptions(true);
assert.equal(form.elements.acts.value, 5);
form.elements.rung.value = 25;
form.elements.acts.value = 1;
listeners.get("change")();
assert.match(note.textContent, /5 ball.*Heavy and light balls.*draught/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.jugglerInfo(1), 25);
assert.equal(host.jugglerInfo(3), 1);
for (const [key, down] of [["a", true], ["ArrowLeft", true], ["a", false], ["ArrowLeft", false],
  ["d", true], ["ArrowRight", true], ["ArrowRight", false], ["d", false]]) {
  assert.ok(host.jugglerControl({ key, preventDefault() {} }, down));
}
host.clearJugglerControls(9n);
assert.deepEqual(controls, [0, 0, 0, 3, 1, 1, 1, 4, [9n, 0]]);
host.destroyJugglerRun();
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
const environment = createJugglerEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 40 });
assert.equal(environment.n_actions, 2);
let verdict;
for (let i = 0; i < 180 && !verdict; i++) {
  const [observation] = environment.step();
  if (observation.outcome) verdict = observation;
}
assert.equal(verdict.outcome.scalar, -1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.close();
assert.throws(() => createJugglerEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
console.log("PASS: Juggler WASM held controls, focus cleanup, course rendering, options, one-frame agent controls, and verdict");
