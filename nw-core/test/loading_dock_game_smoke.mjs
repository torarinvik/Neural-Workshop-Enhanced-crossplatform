import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createLoadingDockEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_loading_dock();
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const attention = TASK_IDS_BY_CATEGORY[2];
assert.equal(attention[attention.indexOf("stagehand") + 1], "loading_dock");
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = length => new Uint8Array(api.memory.buffer, Number(buffer), Number(length));
const hub = decode(view(api.nw_taskhub_write(buffer, capacity, 2n, 23n, 0n, 912n, 684n)));
assert.ok(hub.some(cmd => cmd.kind === Kind.TEXT && cmd.text === "Loading Dock"));
const create = (rung, trials = 1n) => api.nw_api_v1_create(task, 1n, rung, trials, 1n, 0n, 0n, 0n, 17n);
assert.equal(create(2n), -3n);
const run = create(1n);
let now = 0n;
let sequence = 0n;
const event = (kind, code, x = 500000n, y = 500000n) =>
  api.nw_api_v1_dispatch(run, kind, now, sequence++, code, 0n, 0n, 0n, x, y, 0n);
const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 1n, 912n, 684n)));
const text = value => frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes(value));
const info = field => api.nw_api_v1_loading_dock_info(run, BigInt(field));
const forklift = () => frame().find(cmd => cmd.kind === Kind.POLYGON && cmd.color === 0xf08c28ff);
const advance = timestamp => {
  now = timestamp;
  return api.nw_api_v1_advance(run, now, 0n, sequence++);
};
assert.ok(text("Press Space"));
assert.equal(event(2n, 1n), 1n);
assert.ok(text("OSLO: a blue crate."));
const initial = forklift();
assert.ok(initial);
assert.equal(event(2n, 4n), 1n);
assert.equal(event(2n, 87n), 1n);
assert.equal(event(3n, 4n), 1n);
assert.equal(advance(100n), 1n);
const moved = forklift();
assert.notEqual(moved.b, initial.b);
assert.equal(event(9n, 0n), 1n);
assert.equal(advance(200n), 1n);
assert.deepEqual(forklift(), moved);
const audioLength = api.nw_loading_dock_audio(run, buffer, capacity);
assert.ok(audioLength > 0n && view(audioLength).some(byte => byte !== 0));
assert.equal(event(5n, 0n, 565517n, 462508n), 1n);
assert.equal(event(6n, 0n, 565517n, 462508n), 1n);
assert.equal(advance(216n), 1n);
assert.equal(info(7), 3n);
assert.ok(text("OSLO was sent without its order"));
assert.equal(advance(2715n), 1n);
assert.equal(info(0), 2n);
assert.equal(advance(2716n), 1n);
assert.equal(info(0), 3n);
assert.ok(text("0 of 1 passed"));
assert.equal(api.nw_api_v1_destroy(run), 0n);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const LOADING_DOCK_SETTINGS"), html.indexOf("const GUNSLINGER_SETTINGS"));
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
let host;
host = vm.createContext({
  exports: api, framePtr: Number(buffer), FRAME_CAPACITY: Number(capacity), TextDecoder, view,
  canvas: { width: 912, height: 684, focus() {} }, screen: "taskhub",
  document: { getElementById: id => id === "loading-dock-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "loading_dock",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openLoadingDockOptions(true);
assert.equal(form.elements.rounds.value, 5);
form.elements.rung.value = 25;
form.elements.rounds.value = 1;
listeners.get("change")();
assert.equal(note.textContent, "Rung 25: 6 trucks, up to 3 crates each.  The camera cuts.  Marked crates.  A busy floor.");
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.loadingDockInfo(1), 25);
assert.equal(host.loadingDockInfo(3), 1);
host.destroyLoadingDockRun();
api.nw_frame_free(buffer);

const canvas = { width: 912, height: 684 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  fillRect() {}, strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {},
  moveTo() {}, lineTo() {}, closePath() {},
  clearRect() { pixels.fill(0); },
  fillText() {
    if (this.fillStyle === "rgba(255,64,64,1.000)") {
      pixels.set([255, 64, 64, 255], pixels.length - 4);
      pixels.set([255, 64, 64, 255], pixels.length - 4 - canvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};
const environment = createLoadingDockEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 60 });
assert.equal(environment.n_actions, 20);
let verdict;
for (const port of [15, 9, 3, 10, 5, 5, 12, 13]) {
  const [observation] = environment.step(port);
  assert.equal(observation.audio_rate, 22050);
  verdict = observation;
}
assert.equal(verdict.outcome.scalar, -1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.close();
console.log("PASS: Loading Dock WASM held controls, focus loss, order board, stereo audio, saved options, and stepped verdict");
