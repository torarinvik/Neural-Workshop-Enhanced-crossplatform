import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createBalanceEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_balance();
assert.equal(task, 2560266987n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const attention = TASK_IDS_BY_CATEGORY[2];
assert.equal(attention[attention.indexOf("juggler") + 1], "balance");
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = size => new Uint8Array(api.memory.buffer, Number(buffer), Number(size));
const noteLength = api.nw_balance_options_note(buffer, capacity, 20n);
assert.equal(new TextDecoder().decode(view(noteLength)), "Rung 20: 4 flags, a 1.2 m pole.  Gusts.  The pole changes length partway.");
const create = (rung, seed = 17n) => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, seed);
assert.equal(create(2n), -3n);
const run = create(1n);
let now = 0n;
let seq = 0n;
const dispatch = (kind, code, value = 0n) =>
  api.nw_api_v1_dispatch(run, kind, now, seq++, code, value, 0n, 0n, 500000n, 500000n, 0n);
const info = field => api.nw_api_v1_balance_info(run, BigInt(field));
const advance = () => {
  now += 25n;
  return api.nw_api_v1_advance(run, now, 0n, seq++);
};
const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n)));
const label = text => frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes(text));
assert.ok(label("Press Space"));
assert.equal(dispatch(5n, 0n), 1n);
assert.equal(info(5), 15000n);
assert.equal(info(12), 2n);
assert.ok(label("Keep the pole up"));
assert.equal(dispatch(2n, 5n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(13), 1n);
assert.ok(info(5) > 15000n);
assert.equal(dispatch(2n, 3n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(13), -1n);
assert.equal(dispatch(3n, 3n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(13), 1n);
assert.equal(dispatch(9n, 0n), 1n);
assert.equal(advance(), 1n);
assert.equal(info(13), 0n);
for (let i = 0; i < 180 && info(0) === 1n; i++) assert.equal(advance(), 1n);
assert.equal(info(0), 2n);
assert.equal(info(7), 2n);
assert.ok(label("The pole fell"));
const deadline = info(10);
assert.equal(api.nw_api_v1_advance(run, deadline - 1n, 0n, seq++), 2n);
assert.equal(api.nw_api_v1_advance(run, deadline, 0n, seq++), 1n);
assert.equal(info(0), 3n);
assert.equal(api.nw_api_v1_destroy(run), 0n);

const pulse = create(1n);
assert.equal(api.nw_balance_agent_event(pulse, 0, 2n), 1n);
assert.equal(api.nw_balance_agent_event(pulse, 0, 0n), 1n);
assert.equal(api.nw_balance_agent_event(pulse, 0.025, -1n), 1n);
assert.equal(api.nw_api_v1_balance_info(pulse, 13n), -1n);
assert.equal(api.nw_balance_agent_event(pulse, 0.050, -1n), 1n);
assert.equal(api.nw_api_v1_balance_info(pulse, 13n), 0n);
assert.equal(api.nw_api_v1_destroy(pulse), 0n);
api.nw_frame_free(buffer);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const BALANCE_SETTINGS"), html.indexOf("const JUGGLER_SETTINGS"));
const storage = new Map();
const listeners = new Map();
const note = {};
const form = {
  hidden: true,
  elements: {
    rung: { focus() {}, addEventListener: (event, callback) => listeners.set(event, callback) },
    courses: {}, adaptive: {},
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
  document: { getElementById: id => id === "balance-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "balance",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  apiDispatchAction: (_handle, action) => { controls.push(action); return 2n; },
  apiDispatchLifecycle: (_handle, kind, value) => controls.push([kind, value]),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openBalanceOptions(true);
assert.equal(form.elements.courses.value, 5);
form.elements.rung.value = 25;
form.elements.courses.value = 1;
listeners.get("change")();
assert.match(note.textContent, /5 flags.*Gusts.*changes length/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.balanceInfo(1), 25);
assert.equal(host.balanceInfo(3), 1);
for (const [key, down] of [["a", true], ["ArrowLeft", true], ["a", false], ["ArrowLeft", false],
  ["d", true], ["ArrowRight", true], ["ArrowRight", false], ["d", false]]) {
  assert.ok(host.balanceControl({ key, preventDefault() {} }, down));
}
host.clearBalanceControls(9n);
assert.deepEqual(controls, [0, 0, 0, 3, 1, 1, 1, 4, [9n, 0]]);
host.destroyBalanceRun();
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
const environment = createBalanceEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 40 });
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
assert.throws(() => createBalanceEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
console.log("PASS: Balance WASM held controls, focus cleanup, course rendering, options, one-frame agent controls, and verdict");
