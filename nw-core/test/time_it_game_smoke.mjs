import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createTimeItEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_time_it();
assert.equal(task, 46880388n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const perception = TASK_IDS_BY_CATEGORY[3];
const card = perception.indexOf("time_it");
assert.ok(card >= 0);
assert.equal(perception[card - 1], "touching");
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = size => new Uint8Array(api.memory.buffer, Number(buffer), Number(size));
const noteLength = api.nw_time_it_options_note(buffer, capacity, 20n);
assert.equal(new TextDecoder().decode(view(noteLength)), "Rung 20: +-75 ms.  roll, slow, bounce, throw");
const create = (rung, seed = 17n) => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, seed);
assert.equal(create(2n), -3n);
for (const [rung, kind, at, expected] of [
  [1n, 0n, 2325n, 1n], [7n, 1n, 200n, 2n], [10n, 2n, 3100n, 3n], [13n, 3n, 0n, 4n],
]) {
  const run = create(rung);
  let now = 0n;
  let seq = 0n;
  const dispatch = (kind, code) =>
    api.nw_api_v1_dispatch(run, kind, now, seq++, code, 0n, 0n, 0n, 500000n, 500000n, 0n);
  const info = field => api.nw_api_v1_time_it_info(run, BigInt(field));
  const advance = () => {
    now += 25n;
    return api.nw_api_v1_advance(run, now, 0n, seq++);
  };
  const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n)));
  const label = text => frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes(text));
  assert.ok(label("Press Space"));
  assert.equal(dispatch(rung === 7n ? 5n : 2n, rung === 7n ? 0n : 1n), 1n);
  assert.equal(info(4), kind);
  assert.equal(info(11), -1n);
  assert.equal(dispatch(5n, 0n), 2n);
  assert.equal(api.nw_time_it_audio(run, buffer, capacity), 0n);
  assert.equal(advance(), 1n);
  const length = api.nw_time_it_audio(run, buffer, capacity);
  assert.equal(length, 2204n);
  assert.ok(view(length).some(sample => sample !== 0));
  assert.equal(api.nw_time_it_audio(run, buffer, capacity), 0n);
  while (info(0) === 1n && (at === 0n || now < at)) assert.equal(advance(), 1n);
  if (at > 0n) {
    assert.equal(dispatch(2n, 1n), 1n);
    assert.equal(dispatch(2n, 1n), 2n);
    assert.equal(advance(), 1n);
  }
  assert.equal(info(0), 2n);
  assert.equal(info(7), expected);
  assert.ok(label(expected === 1n ? "On the mark" : expected === 4n ? "No press" : expected === 2n ? "early" : "late"));
  const deadline = info(10);
  assert.equal(api.nw_api_v1_advance(run, deadline - 1n, 0n, seq++), 2n);
  assert.equal(api.nw_api_v1_advance(run, deadline, 0n, seq++), 1n);
  assert.equal(info(0), 3n);
  assert.equal(api.nw_api_v1_destroy(run), 0n);
}
api.nw_frame_free(buffer);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const TIME_IT_SETTINGS"), html.indexOf("const BEAT_SETTINGS"));
const storage = new Map();
const listeners = new Map();
const note = {};
const form = {
  hidden: true,
  elements: {
    rung: { focus() {}, addEventListener: (event, callback) => listeners.set(event, callback) },
    shots: {}, adaptive: {},
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
  document: { getElementById: id => id === "time-it-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "time_it",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openTimeItOptions(true);
assert.equal(form.elements.shots.value, 5);
form.elements.rung.value = 25;
form.elements.shots.value = 1;
listeners.get("change")();
assert.match(note.textContent, /\+-60 ms.*roll, slow, bounce, throw/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.timeItInfo(1), 25);
assert.equal(host.timeItInfo(3), 1);
host.destroyTimeItRun();
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
const environment = createTimeItEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 40 });
assert.equal(environment.n_actions, 1);
for (let frame = 0; frame < 93; frame++) {
  const [observation] = environment.step();
  assert.equal(observation.audio_rate, 22050);
  assert.equal(observation.audio_channels, 2);
  assert.equal(observation.outcome, undefined);
}
const [verdict] = environment.step(0);
assert.equal(verdict.outcome.scalar, 1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.close();
assert.throws(() => createTimeItEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
console.log("PASS: Time It WASM motion, timed press and miss, options, audio, and agent verdict");
