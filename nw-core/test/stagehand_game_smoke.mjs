import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createStagehandEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_stagehand();
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const attention = TASK_IDS_BY_CATEGORY[2];
assert.equal(attention[attention.indexOf("safecracker") + 1], "stagehand");
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = size => new Uint8Array(api.memory.buffer, Number(buffer), Number(size));
const hub = decode(view(api.nw_taskhub_write(buffer, capacity, 2n, 22n, 0n, 912n, 684n)));
assert.ok(hub.some(cmd => cmd.kind === Kind.TEXT && cmd.text === "Stagehand"));
const noteLength = api.nw_stagehand_options_note(buffer, capacity, 20n);
assert.match(new TextDecoder().decode(view(noteLength)), /6 cues.*camera changes/);
const create = (rung, seed = 17n) => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, seed);
assert.equal(create(2n), -3n);
const run = create(1n);
let now = 0n;
let sequence = 0n;
const event = (kind, code, x = 500000n, y = 500000n) =>
  api.nw_api_v1_dispatch(run, kind, now, sequence++, code, 0n, 0n, 0n, x, y, 0n);
const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 1n, 912n, 684n)));
const info = field => api.nw_api_v1_stagehand_info(run, BigInt(field));
assert.ok(frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes("Press Space")));
assert.equal(event(2n, 1n), 1n);
assert.ok(frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text === "Move the lamp in front of the chair."));
assert.ok(frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes("next: Cue the thunder")));
assert.equal(event(5n, 0n), 1n);
assert.equal(event(6n, 0n), 1n);
assert.equal(event(9n, 0n), 2n);
assert.equal(event(2n, 76n), 1n);
now = 50n;
assert.equal(api.nw_api_v1_advance(run, now, 0n, sequence++), 1n);
assert.equal(info(7), 4n);
assert.ok(frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text === "That was the wrong cue"));
const length = api.nw_stagehand_audio(run, buffer, capacity);
assert.ok(length > 0n && view(length).some(byte => byte !== 0));
assert.equal(api.nw_api_v1_destroy(run), 0n);
api.nw_frame_free(buffer);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const STAGEHAND_SETTINGS"), html.indexOf("const LOADING_DOCK_SETTINGS"));
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
  document: { getElementById: id => id === "stagehand-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "stagehand",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openStagehandOptions(true);
assert.equal(form.elements.rounds.value, 5);
form.elements.rung.value = 25;
form.elements.rounds.value = 1;
listeners.get("change")();
assert.match(note.textContent, /7 cues.*camera changes/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.stagehandInfo(1), 25);
assert.equal(host.stagehandInfo(3), 1);
let stopped = false;
host.stopSpeaker = () => { stopped = true; };
vm.runInContext(`
  stagehandAudio = { close: () => Promise.resolve() };
  stagehandAudioSources.add({ stop: stopSpeaker });
  stagehandInfo = () => 2;
  playStagehandTones();
`, host);
assert.ok(stopped, "a verdict stops scheduled speaker audio");
host.destroyStagehandRun();
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
const environment = createStagehandEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 60 });
assert.equal(environment.n_actions, 19);
const ports = [4, 5, 5, 12, 6, 6, 7, 7, 4, 7, 5, 5, 13, 18];
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
console.log("PASS: Stagehand WASM prop drag, correct and wrong cues, stereo audio, options, and stepped verdict");
