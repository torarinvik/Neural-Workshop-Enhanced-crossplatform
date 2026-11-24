import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createGunslingerEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_gunslinger();
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const attention = TASK_IDS_BY_CATEGORY[2];
assert.equal(attention[attention.indexOf("loading_dock") + 1], "gunslinger");
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = length => new Uint8Array(api.memory.buffer, Number(buffer), Number(length));
const hub = decode(view(api.nw_taskhub_write(buffer, capacity, 2n, 24n, 0n, 912n, 684n)));
assert.ok(hub.some(cmd => cmd.kind === Kind.TEXT && cmd.text === "Gunslinger"));
const create = rung => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, 17n);
assert.equal(create(2n), -3n);
const run = create(4n);
let now = 0n;
let sequence = 0n;
const event = (kind, code, x = 500000n, y = 500000n) =>
  api.nw_api_v1_dispatch(run, kind, now, sequence++, code, 0n, 0n, 0n, x, y, 0n);
const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 1n, 912n, 684n)));
const text = value => frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text === value);
const info = field => api.nw_api_v1_gunslinger_info(run, BigInt(field));
const sight = () => frame().find(cmd => cmd.kind === Kind.CIRCLE && cmd.color === 0xff3c28ff);
const advance = timestamp => {
  now = timestamp;
  return api.nw_api_v1_advance(run, now, 0n, sequence++);
};
assert.ok(text("Press Space or click to start"));
assert.equal(event(2n, 1n), 1n);
assert.ok(text("SPACE"));
assert.equal(info(12), 0n);
assert.equal(event(2n, 1n), 1n);
assert.ok(text("COCKED"));
assert.equal(info(12), 1n);
const before = sight();
assert.equal(event(4n, 0n, 600000n, 525000n), 1n);
assert.notEqual(sight().a, before.a);
assert.equal(advance(50n), 1n);
const audioLength = api.nw_gunslinger_audio(run, buffer, capacity);
assert.ok(audioLength > 0n && view(audioLength).some(byte => byte !== 0));
assert.equal(event(5n, 0n, 600000n, 525000n), 1n);
assert.equal(advance(67n), 1n);
assert.equal(info(7), 3n);
assert.equal(info(11), 1n);
assert.ok(text("You fired first"));
assert.equal(advance(2566n), 1n);
assert.equal(info(0), 2n);
assert.equal(advance(2568n), 1n);
assert.equal(info(0), 3n);
assert.ok(text("0 of 1 passed   highest rung passed 0"));
assert.equal(api.nw_api_v1_destroy(run), 0n);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const GUNSLINGER_SETTINGS"), html.indexOf("const BALANCE_SETTINGS"));
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
  document: { getElementById: id => id === "gunslinger-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "gunslinger",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openGunslingerOptions(true);
assert.equal(form.elements.rounds.value, 5);
form.elements.rung.value = 25;
form.elements.rounds.value = 1;
listeners.get("change")();
assert.equal(note.textContent, "Rung 25: he fires 0.9 seconds after he draws.  Cock the hammer.  5 men in the street.  He feints.");
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.gunslingerInfo(1), 25);
assert.equal(host.gunslingerInfo(3), 1);
host.destroyGunslingerRun();
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
const environment = createGunslingerEnvironment(context, { seed: 17, rung: 4, trials: 1, frameHz: 60 });
assert.equal(environment.n_actions, 15);
const [cock] = environment.step(14);
assert.equal(cock.audio_rate, 22050);
const [verdict] = environment.step(12);
assert.equal(verdict.outcome.scalar, -1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.close();
console.log("PASS: Gunslinger WASM aim, hammer, stereo audio, saved options, feedback, and stepped verdict");
