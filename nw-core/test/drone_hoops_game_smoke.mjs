import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createDroneHoopsEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_drone_hoops();
assert.equal(task, 2910612837n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const attention = TASK_IDS_BY_CATEGORY[2];
assert.equal(attention[attention.indexOf("echo_cave") + 1], "drone_hoops");
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = size => new Uint8Array(api.memory.buffer, Number(buffer), Number(size));
const noteLength = api.nw_drone_hoops_options_note(buffer, capacity, 20n);
assert.match(new TextDecoder().decode(view(noteLength)), /Rung 20 has \d+ hoops.*Follow the bell/);
const create = (rung, seed = 17n) => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, seed);
assert.equal(create(2n), -3n);
const run = create(10n);
let now = 0n;
let sequence = 0n;
const event = (kind, code, value = 0n, x = 700000n, y = 590000n) =>
  api.nw_api_v1_dispatch(run, kind, now, sequence++, code, value, 0n, 0n, x, y, 0n);
const tick = () => {
  now += 100n;
  return api.nw_api_v1_advance(run, now, 0n, sequence++);
};
const info = field => api.nw_api_v1_drone_hoops_info(run, BigInt(field));
const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 1n, 912n, 684n)));
assert.ok(frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes("Press Space")));
assert.equal(event(5n, 0n), 1n);
assert.equal(info(0), 1n);
assert.ok(frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes("Follow the bell")));
assert.ok(frame().some(cmd => cmd.kind === Kind.LINE));
assert.equal(event(4n, 0n), 1n);
assert.equal(event(6n, 0n), 1n);
assert.equal(event(4n, 0n), 2n);
assert.equal(event(7n, 0n, -400000n), 1n);
const height = info(14);
assert.equal(tick(), 1n);
assert.ok(info(14) > height);
assert.equal(event(2n, 1n), 1n);
assert.equal(event(3n, 1n), 1n);
assert.equal(event(9n, 0n), 2n);
const speaker = api.nw_drone_hoops_speaker_audio(run, buffer, capacity);
assert.ok(speaker > 0n && view(speaker).every(byte => byte === 0));
let sounded = false;
for (let i = 0; i < 750 && info(0) === 1n; i++) {
  assert.equal(tick(), 1n);
  const length = api.nw_drone_hoops_speaker_audio(run, buffer, capacity);
  sounded ||= view(length).some(byte => byte !== 0);
}
assert.ok(sounded);
assert.equal(info(0), 2n);
assert.equal(info(7), 3n);
assert.equal(api.nw_api_v1_advance(run, info(10), 0n, sequence++), 1n);
assert.equal(info(0), 3n);
assert.equal(api.nw_api_v1_destroy(run), 0n);

const pulse = create(16n);
assert.equal(api.nw_drone_hoops_agent_event(pulse, 0, 10n), 1n);
assert.equal(api.nw_drone_hoops_agent_mask(pulse, 1024n), -6n);
assert.equal(api.nw_drone_hoops_agent_mask(pulse, 513n), 1n);
assert.equal(api.nw_drone_hoops_agent_event(pulse, 0.05, -1n), 1n);
assert.ok(api.nw_api_v1_drone_hoops_info(pulse, 14n) < 2500n);
const length = api.nw_drone_hoops_audio(pulse, buffer, capacity);
assert.ok(length > 0n && view(length).some(byte => byte !== 0));
assert.equal(api.nw_api_v1_destroy(pulse), 0n);
api.nw_frame_free(buffer);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const DRONE_HOOPS_SETTINGS"), html.indexOf("const FIELD_MANUAL_SETTINGS"));
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
  document: { getElementById: id => id === "drone-hoops-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "drone_hoops",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openDroneHoopsOptions(true);
assert.equal(form.elements.rounds.value, 5);
form.elements.rung.value = 25;
form.elements.rounds.value = 1;
listeners.get("change")();
assert.match(note.textContent, /Rung 25 has \d+ hoops.*Follow the bell/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.droneHoopsInfo(1), 25);
assert.equal(host.droneHoopsInfo(3), 1);
host.destroyDroneHoopsRun();
api.nw_frame_free(formBuffer);

const canvas = { width: 912, height: 684 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
let scenerySharesVerdictColor = false;
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
    const color = colors[this.fillStyle] ?? (scenerySharesVerdictColor ? [64, 255, 64, 255] : null);
    if (color) {
      pixels.set(color, pixels.length - 4);
      pixels.set(color, pixels.length - 4 - canvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};
const environment = createDroneHoopsEnvironment(context, { seed: 17, rung: 10, trials: 1, frameHz: 10 });
assert.equal(environment.n_actions, 10);
assert.deepEqual(environment.act([5, 8]).ports, [5, 8]);
assert.equal(environment.act([1]).ok, false);
scenerySharesVerdictColor = true;
assert.equal(environment.step()[0].outcome, undefined);
scenerySharesVerdictColor = false;
let verdict;
for (let index = 0; index < 750; index++) {
  const [observation] = environment.step();
  assert.equal(observation.audio_rate, 22050);
  if (observation.outcome) {
    verdict = observation;
    break;
  }
}
assert.equal(verdict.outcome.scalar, -1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.close();
console.log("PASS: Drone Hoops WASM pointer hold/release, wheel height, delayed speaker PCM, options, simultaneous agent controls and verdict");
