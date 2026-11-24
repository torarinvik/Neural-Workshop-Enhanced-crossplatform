import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createLanderEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_lander();
assert.equal(task, 2771681963n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const attention = TASK_IDS_BY_CATEGORY[2];
assert.equal(attention[attention.indexOf("marble_maze") + 1], "lander");
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = size => new Uint8Array(api.memory.buffer, Number(buffer), Number(size));
const noteLength = api.nw_lander_options_note(buffer, capacity, 20n);
assert.equal(new TextDecoder().decode(view(noteLength)), "Rung 20: a 9 m pad; down 2.0, across 1.5 m/s, tilt 8 degrees at most.  Fuel 22 s.  With rough ground, gusts, hidden gravity and engine, a moving pad.");
const create = (rung, seed = 17n) => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, seed);
assert.equal(create(2n), -3n);
const run = create(1n);
let now = 0n;
let seq = 0n;
const dispatch = (kind, code, value = 0n) =>
  api.nw_api_v1_dispatch(run, kind, now, seq++, code, value, 0n, 0n, 500000n, 500000n, 0n);
const info = field => api.nw_api_v1_lander_info(run, BigInt(field));
const advance = () => {
  now += 50n;
  return api.nw_api_v1_advance(run, now, 0n, seq++);
};
const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n)));
const label = text => frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes(text));
assert.ok(label("Press Space"));
assert.equal(dispatch(5n, 0n), 1n);
assert.equal(info(6), 58000n);
assert.equal(info(14), -1n);
assert.ok(label("Land on the pad") && label("fuel unlimited"));
assert.equal(dispatch(2n, 4n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(15), 1n);
assert.ok(info(12) > 0n);
assert.equal(dispatch(2n, 3n), 1n);
assert.equal(advance(), 1n);
assert.ok(info(13) > 0n && info(11) < 0n);
assert.equal(dispatch(2n, 5n), 1n);
const angle = info(13);
assert.equal(advance(), 1n);
assert.equal(info(13), angle);
assert.equal(dispatch(3n, 3n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(13), 0n);
assert.equal(dispatch(9n, 0n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(15), 0n);
for (let index = 0; index < 250 && info(0) === 1n; index++) assert.equal(advance(), 1n);
assert.equal(info(0), 2n);
assert.equal(info(7), 5n);
assert.ok(label("Too fast down"));
const deadline = info(10);
assert.equal(api.nw_api_v1_advance(run, deadline - 1n, 0n, seq++), 2n);
assert.equal(api.nw_api_v1_advance(run, deadline, 0n, seq++), 1n);
assert.equal(info(0), 3n);
assert.equal(api.nw_api_v1_destroy(run), 0n);

const pulse = create(7n);
assert.equal(api.nw_lander_agent_event(pulse, 0, 5n), 1n);
assert.equal(api.nw_lander_agent_event(pulse, 0, 3n), 1n);
assert.equal(api.nw_lander_agent_event(pulse, 0.050, -1n), 1n);
assert.equal(api.nw_api_v1_lander_info(pulse, 15n), 1n);
assert.ok(api.nw_api_v1_lander_info(pulse, 13n) > 0n);
assert.equal(api.nw_lander_agent_event(pulse, 0.100, -1n), 1n);
assert.equal(api.nw_api_v1_lander_info(pulse, 15n), 0n);
assert.equal(api.nw_api_v1_destroy(pulse), 0n);
api.nw_frame_free(buffer);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const LANDER_SETTINGS"), html.indexOf("const GLIDER_SETTINGS"));
const storage = new Map();
const listeners = new Map();
const note = {};
const form = {
  hidden: true,
  elements: {
    rung: { focus() {}, addEventListener: (event, callback) => listeners.set(event, callback) },
    landings: {}, adaptive: {},
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
  document: { getElementById: id => id === "lander-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "lander",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  apiDispatchAction: (_handle, action) => { controls.push(action); return 2n; },
  apiDispatchLifecycle: (_handle, kind, value) => controls.push([kind, value]),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openLanderOptions(true);
assert.equal(form.elements.landings.value, 5);
form.elements.rung.value = 25;
form.elements.landings.value = 1;
listeners.get("change")();
assert.match(note.textContent, /tilt 8 degrees.*hidden gravity and engine.*moving pad/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.landerInfo(1), 25);
assert.equal(host.landerInfo(3), 1);
for (const [key, down] of [["a", true], ["ArrowLeft", true], ["a", false], ["ArrowLeft", false],
  ["d", true], ["ArrowRight", true], ["ArrowRight", false], ["d", false]]) {
  assert.ok(host.landerControl({ key, preventDefault() {} }, down));
}
host.clearLanderControls(9n);
assert.deepEqual(controls, [1, 1, 1, 7, 2, 2, 2, 8, [9n, 0]]);
host.destroyLanderRun();
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
const environment = createLanderEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 40 });
assert.equal(environment.n_actions, 5);
let verdict;
for (let i = 0; i < 420 && !verdict; i++) {
  const [observation] = environment.step();
  if (observation.outcome) verdict = observation;
}
assert.equal(verdict.outcome.scalar, -1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.close();
assert.throws(() => createLanderEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
console.log("PASS: Lander WASM combined controls, focus cleanup, terrain rendering, options, one-frame agent controls, and verdict");
