import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createCatchEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_catch();
assert.equal(task, 1116268876n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const attention = TASK_IDS_BY_CATEGORY[2];
assert.equal(attention[attention.indexOf("glider") + 1], "catch");
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = size => new Uint8Array(api.memory.buffer, Number(buffer), Number(size));
const noteLength = api.nw_catch_options_note(buffer, capacity, 20n);
assert.equal(new TextDecoder().decode(view(noteLength)), "Rung 20: 8 balls, one drop allowed, two baskets, fog, swinging camera.");
const create = (rung, seed = 17n) => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, seed);
assert.equal(create(2n), -3n);
const run = create(20n);
let now = 0n;
let sequence = 0n;
const event = (kind, code, value = 0n, x = 700000n, y = 400000n) =>
  api.nw_api_v1_dispatch(run, kind, now, sequence++, code, value, 0n, 0n, x, y, 0n);
const tick = () => {
  now += 25n;
  return api.nw_api_v1_advance(run, now, 0n, sequence++);
};
const info = field => api.nw_api_v1_catch_info(run, BigInt(field));
const label = text => decode(view(api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n)))
  .some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes(text));
assert.ok(label("Press Space"));
assert.equal(event(5n, 0n), 1n);
assert.ok(label("Red basket on the keys"));
assert.equal(info(12), 2n);
assert.equal(event(2n, 3n), 1n);
assert.equal(event(2n, 4n), 1n);
assert.equal(event(4n, 0n), 1n);
assert.equal(tick(), 1n);
assert.ok(info(13) < -3000n && info(14) > 6000n);
assert.ok(info(15) !== 3000n || info(16) !== 6000n);
assert.equal(event(9n, 0n), 1n);
const red = [info(13), info(14)];
let sounded = false;
for (let i = 0; i < 600 && info(0) === 1n; i++) {
  assert.equal(tick(), 1n);
  const length = api.nw_catch_audio(run, buffer, capacity);
  sounded ||= view(length).some(value => value !== 0);
}
assert.ok(sounded && label("balls dropped"));
assert.deepEqual([info(13), info(14)], red);
assert.equal(info(7), 2n);
assert.equal(api.nw_api_v1_advance(run, info(10), 0n, sequence++), 1n);
assert.equal(info(0), 3n);
assert.equal(api.nw_api_v1_destroy(run), 0n);

const pulse = create(20n);
assert.equal(api.nw_catch_agent_event(pulse, 0, 8n), 1n);
assert.equal(api.nw_catch_agent_mask(pulse, 256n), -6n);
assert.equal(api.nw_catch_agent_mask(pulse, 105n), 1n);
assert.equal(api.nw_catch_agent_event(pulse, 0.05, -1n), 1n);
const basket = field => api.nw_api_v1_catch_info(pulse, BigInt(field));
assert.deepEqual([13, 14, 15, 16].map(basket), [-3600n, 6600n, 3600n, 5400n]);
assert.equal(api.nw_catch_agent_event(pulse, 0.1, -1n), 1n);
assert.deepEqual([13, 14, 15, 16].map(basket), [-3600n, 6600n, 3600n, 5400n]);
assert.equal(api.nw_api_v1_destroy(pulse), 0n);
api.nw_frame_free(buffer);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const CATCH_SETTINGS"), html.indexOf("const ECHO_CAVE_SETTINGS"));
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
  document: { getElementById: id => id === "catch-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "catch",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openCatchOptions(true);
assert.equal(form.elements.rounds.value, 5);
form.elements.rung.value = 25;
form.elements.rounds.value = 1;
listeners.get("change")();
assert.match(note.textContent, /10 balls.*two baskets, fog, swinging camera/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.catchInfo(1), 25);
assert.equal(host.catchInfo(3), 1);
host.destroyCatchRun();
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
const environment = createCatchEnvironment(context, { seed: 17, rung: 20, trials: 1, frameHz: 40 });
assert.equal(environment.n_actions, 8);
const receipt = environment.act([0, 3, 5, 6, 3]);
assert.deepEqual(receipt.ports, [0, 3, 5, 6]);
assert.equal(environment.act([1]).ok, false);
let verdict;
for (let frame = 0; frame < 600; frame++) {
  const [observation] = environment.step();
  assert.equal(observation.audio_rate, 22050);
  assert.equal(observation.audio_channels, 2);
  if (observation.outcome) {
    verdict = observation;
    break;
  }
}
assert.equal(verdict.outcome.scalar, -1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.close();
assert.throws(() => createCatchEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
console.log("PASS: Catch WASM perspective aiming, held keys, focus cleanup, stereo PCM, and simultaneous agent controls");
