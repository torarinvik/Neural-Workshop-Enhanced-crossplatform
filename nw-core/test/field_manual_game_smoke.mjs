import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createFieldManualEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_field_manual();
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const attention = TASK_IDS_BY_CATEGORY[2];
assert.equal(attention[attention.indexOf("drone_hoops") + 1], "field_manual");
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = size => new Uint8Array(api.memory.buffer, Number(buffer), Number(size));
const noteLength = api.nw_field_manual_options_note(buffer, capacity, 20n);
assert.match(new TextDecoder().decode(view(noteLength)), /5 orders.*Orders disappear/);
const create = (rung, seed = 17n) => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, seed);
assert.equal(create(2n), -3n);
const run = create(1n);
let now = 0n;
let sequence = 0n;
const scale = 389 / 640;
const x = Math.round(((912 - 1000 * scale) / 2 + 449.296 * scale) * 1e6 / 912);
const y = Math.round((179 + 335.472 * scale) * 1e6 / 684);
const event = (kind, code, value = 0n) =>
  api.nw_api_v1_dispatch(run, kind, now, sequence++, code, value, 0n, 0n, BigInt(x), BigInt(y), 0n);
const tick = () => {
  now += 50n;
  return api.nw_api_v1_advance(run, now, 0n, sequence++);
};
const info = field => api.nw_api_v1_field_manual_info(run, BigInt(field));
const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 1n, 912n, 684n)));
assert.ok(frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes("Press Space")));
assert.equal(event(2n, 1n), 1n);
assert.ok(frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text === "Flip the red switch."));
assert.equal(event(2n, 24n), 1n);
assert.equal(tick(), 1n);
assert.ok(frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes("SHIFT")));
assert.equal(event(3n, 24n), 1n);
assert.equal(event(9n, 0n), 2n);
assert.ok(!frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes("SHIFT")));
assert.equal(event(4n, 0n), 1n);
assert.equal(event(5n, 0n), 1n);
assert.equal(event(6n, 0n), 1n);
assert.equal(tick(), 1n);
assert.equal(info(0), 2n);
assert.equal(info(7), 1n);
assert.ok(frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text === "Every order carried out"));
const length = api.nw_field_manual_audio(run, buffer, capacity);
assert.ok(length > 0n && view(length).some(byte => byte !== 0));
assert.equal(api.nw_api_v1_advance(run, info(10), 0n, sequence++), 1n);
assert.equal(info(0), 3n);
assert.equal(api.nw_api_v1_destroy(run), 0n);

const pulse = create(20n);
assert.equal(api.nw_field_manual_agent_event(pulse, 0, 25n), 1n);
assert.equal(api.nw_field_manual_agent_event(pulse, 0, 26n), -6n);
for (let i = 1; i <= 65; i++) {
  assert.equal(api.nw_field_manual_agent_event(pulse, i / 10, -1n), 1n);
  assert.ok(api.nw_api_v1_render(pulse, buffer, capacity, 1n, 912n, 684n) > 0n);
}
const hidden = decode(view(api.nw_api_v1_render(pulse, buffer, capacity, 1n, 912n, 684n)));
assert.ok(hidden.some(cmd => cmd.kind === Kind.TEXT && cmd.text === "(the order has gone)"));
assert.equal(api.nw_api_v1_destroy(pulse), 0n);
const older = create(16n);
const newer = create(20n);
assert.equal(api.nw_field_manual_agent_event(older, 0, 25n), 1n);
assert.equal(api.nw_field_manual_agent_event(newer, 0, 25n), 1n);
const renderNewer = () => view(api.nw_api_v1_render(newer, buffer, capacity, 1n, 912n, 684n)).slice();
const beforeDisposal = renderNewer();
assert.ok(beforeDisposal.length > 0);
assert.equal(api.nw_api_v1_destroy(older), 0n);
assert.deepEqual(renderNewer(), beforeDisposal);
assert.equal(api.nw_api_v1_destroy(newer), 0n);
api.nw_frame_free(buffer);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const FIELD_MANUAL_SETTINGS"), html.indexOf("const SAFECRACKER_SETTINGS"));
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
  document: { getElementById: id => id === "field-manual-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "field_manual",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openFieldManualOptions(true);
assert.equal(form.elements.rounds.value, 5);
form.elements.rung.value = 25;
form.elements.rounds.value = 1;
listeners.get("change")();
assert.match(note.textContent, /6 orders.*Orders disappear/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.fieldManualInfo(1), 25);
assert.equal(host.fieldManualInfo(3), 1);
host.destroyFieldManualRun();
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
const environment = createFieldManualEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 60 });
assert.equal(environment.n_actions, 25);
const ports = [7, 7, 2, 8, 2, 8, 2, 12, 13];
let verdict;
for (const port of ports) {
  const [observation] = environment.step(port);
  assert.equal(observation.audio_rate, 22050);
  verdict = observation;
}
assert.equal(verdict.outcome.scalar, 1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.close();
console.log("PASS: Field Manual WASM pointer press and release, Shift, order visibility, audio, options, and stepped verdict");
