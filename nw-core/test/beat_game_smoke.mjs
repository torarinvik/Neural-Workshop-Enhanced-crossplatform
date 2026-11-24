import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, createBeatEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_beat();
assert.equal(task, 4282310537n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const attention = TASK_IDS_BY_CATEGORY[2];
assert.equal(attention[attention.indexOf("crossings") + 1], "keep_the_beat");
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const view = size => new Uint8Array(api.memory.buffer, Number(buffer), Number(size));
const noteLength = api.nw_beat_options_note(buffer, capacity, 20n);
assert.equal(new TextDecoder().decode(view(noteLength)), "Rung 20: carry 12 beats, with a 100 ms window and a metronome reprise.");
const create = (rung, seed = 17n) => api.nw_api_v1_create(task, 1n, rung, 1n, 1n, 0n, 0n, 0n, seed);
assert.equal(create(2n), -3n);
for (const play of [true, false]) {
  const run = create(1n);
  let now = 0n;
  let seq = 0n;
  const dispatch = (kind, code) =>
    api.nw_api_v1_dispatch(run, kind, now, seq++, code, 0n, 0n, 0n, 500000n, 500000n, 0n);
  const info = field => api.nw_api_v1_beat_info(run, BigInt(field));
  const frame = () => decode(view(api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n)));
  const label = text => frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.includes(text));
  assert.ok(label("Press Space"));
  assert.equal(dispatch(play ? 2n : 5n, play ? 1n : 0n), 1n);
  assert.equal(info(4), 6n);
  assert.equal(dispatch(5n, 0n), 2n);
  assert.equal(api.nw_beat_audio(run, buffer, capacity), 0n);
  while (info(0) === 1n && now < 15000n) {
    if (play && now >= 7200n && now <= 11200n && (now - 7200n) % 800n === 0n) {
      assert.equal(dispatch(2n, 1n), 1n);
    }
    now += 25n;
    assert.equal(api.nw_api_v1_advance(run, now, 0n, seq++), 1n);
    const length = api.nw_beat_audio(run, buffer, capacity);
    assert.ok(length > 0n && length <= 2204n && length % 4n === 0n);
    if (now === 825n) assert.ok(view(length).some(sample => sample !== 0));
    if (now === 7500n) {
      assert.ok(view(length).every(sample => sample === 0));
      assert.ok(label("keep it going"));
    }
  }
  assert.equal(info(0), 2n);
  assert.equal(info(7), play ? 1n : 2n);
  assert.equal(info(13), play ? 6n : 0n);
  assert.ok(label(play ? "6 of 6 beats kept" : "0 of 6 beats kept -- 5 needed"));
  const deadline = info(10);
  assert.equal(api.nw_api_v1_advance(run, deadline - 1n, 0n, seq++), 2n);
  assert.equal(api.nw_api_v1_advance(run, deadline, 0n, seq++), 1n);
  assert.equal(info(0), 3n);
  assert.equal(api.nw_api_v1_destroy(run), 0n);
}
api.nw_frame_free(buffer);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const BEAT_SETTINGS"), html.indexOf("const CATCH_SETTINGS"));
const storage = new Map();
const listeners = new Map();
const note = {};
const form = {
  hidden: true,
  elements: {
    rung: { focus() {}, addEventListener: (event, callback) => listeners.set(event, callback) },
    songs: {}, adaptive: {},
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
  document: { getElementById: id => id === "keep-the-beat-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "keep_the_beat",
  apiCreateRun: (id, options, seed) => api.nw_api_v1_create(id, 1n, ...options, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openBeatOptions(true);
assert.equal(form.elements.songs.value, 5);
form.elements.rung.value = 25;
form.elements.songs.value = 1;
listeners.get("change")();
assert.match(note.textContent, /80 ms window and a metronome reprise/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(host.beatInfo(1), 25);
assert.equal(host.beatInfo(3), 1);
host.destroyBeatRun();
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
const environment = createBeatEnvironment(context, { seed: 17, rung: 1, trials: 1, frameHz: 40 });
assert.equal(environment.n_actions, 1);
let verdict;
for (let frame = 0; frame < 600; frame++) {
  const tap = frame >= 288 && frame <= 448 && (frame - 288) % 32 === 0;
  const [observation] = environment.step(tap ? 0 : undefined);
  assert.equal(observation.audio_rate, 22050);
  assert.equal(observation.audio_channels, 2);
  if (observation.outcome) {
    verdict = observation;
    break;
  }
}
assert.equal(verdict.outcome.scalar, 1);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
environment.close();
assert.throws(() => createBeatEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
console.log("PASS: Keep the Beat WASM timing, curtain, metronome PCM, options, and agent verdict");
