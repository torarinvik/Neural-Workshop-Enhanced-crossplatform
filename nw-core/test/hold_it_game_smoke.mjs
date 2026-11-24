import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, instance, createHoldItEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_hold_it();
assert.equal(task, 3702462192n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const create = (rung = 1n, count = 1n) =>
  api.nw_api_v1_create(task, 1n, rung, count, 0n, 0n, 0n, 0n, 17n);
assert.equal(create(2n), -3n);
assert.equal(create(1n, 2n), -3n);
const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const bytes = length => new Uint8Array(instance.exports.memory.buffer, Number(buffer), Number(length));
const preview = api.nw_hold_it_options_note(buffer, capacity, 13n);
assert.equal(new TextDecoder().decode(bytes(preview)), "Rung 13: within 16%.  A clock ticks at the wrong speed.");
assert.deepEqual(TASK_IDS_BY_CATEGORY[6], ["cookie_thief", "stop_and_switch", "delay", "hold_it", "morning_round"]);
const cards = decode(bytes(api.nw_taskhub_write(buffer, capacity, 6n, 3n, 0n, 912n, 684n)))
  .filter(command => ["Cookie Thief", "Stop & Switch", "Delay", "Hold It"].includes(command.text))
  .map(command => command.text);
assert.deepEqual(cards, ["Cookie Thief", "Stop & Switch", "Delay", "Hold It"]);

for (const ending of [3n, 9n, 10n, 11n]) {
  const run = create();
  assert.ok(run > 0n);
  let sequence = 0n;
  let now = 0n;
  const event = (kind, key = 0n) =>
    api.nw_api_v1_dispatch(run, kind, now, sequence++, key, 0n, 0n, 0n, 500000n, 500000n, 0n);
  const info = field => api.nw_api_v1_hold_it_info(run, BigInt(field));
  const advance = () => {
    now += 25n;
    return api.nw_api_v1_advance(run, now, 0n, sequence++);
  };
  const frame = () => decode(bytes(api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n)));
  const contains = text => frame().some(cmd => cmd.kind === Kind.TEXT && cmd.text.startsWith(text));
  assert.ok(contains("Press Space"));
  assert.equal(event(5n, 1n), 2n);
  assert.equal(event(ending === 3n ? 2n : 5n, ending === 3n ? 1n : 0n), 1n);
  if (ending === 3n) assert.equal(event(3n, 1n), 1n);
  assert.equal(info(0), 1n);
  assert.equal(info(14), -1n);
  assert.equal(api.nw_hold_it_audio(run, buffer, capacity), 0n);
  let lit = false;
  let heard = false;
  while (!info(9) && now < 5000n) {
    assert.equal(advance(), 1n);
    lit ||= info(7) === 1n;
    const audioLength = api.nw_hold_it_audio(run, buffer, capacity);
    assert.equal(audioLength, 2204n);
    const signal = bytes(audioLength).some(value => value !== 0);
    if (now <= 800n) assert.equal(signal, false);
    heard ||= signal;
    assert.equal(api.nw_hold_it_audio(run, buffer, capacity), 0n);
    assert.equal(info(14), -1n);
  }
  assert.ok(lit && heard);
  assert.equal(info(9), 1n);
  assert.ok(contains("Hold now"));
  assert.ok(!contains("asked "));
  assert.equal(api.nw_api_v1_read_state(run, buffer, capacity), 112n);
  assert.equal(event(2n, 1n), 1n);
  assert.equal(event(2n, 1n), 2n);
  for (let tick = 0; tick < 40; tick++) advance();
  assert.equal(info(10), 1n);
  assert.equal(info(7), 1n);
  assert.equal(info(15), -1n);
  assert.ok(contains("holding..."));
  assert.equal(event(ending, ending === 3n ? 1n : 0n), 1n);
  advance();
  assert.equal(info(0), 2n);
  assert.equal(info(10), 0n);
  assert.equal(info(15), 1000n);
  assert.ok(contains("asked ") && contains("held 1.00 s"));
  now += 2975n;
  assert.equal(advance(), 1n);
  assert.equal(info(0), 3n);
  assert.equal(api.nw_api_v1_destroy(run), 0n);
  assert.equal(info(0), -1n);
}

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
for (const hook of [
  'if (isHoldItTask()) {',
  'apiDispatchKey(ensureHoldItRun(), API_KEY.space, event)',
  'apiDispatchKeyUp(holdItRun, event)',
  'apiDispatchLifecycle(holdItRun, API_EVENT.focus, 0)',
  'apiDispatchLifecycle(holdItRun, API_EVENT.visibility, 0)',
  'localStorage.setItem(HOLD_IT_SETTINGS, JSON.stringify(options))',
]) assert.ok(html.includes(hook), hook);
const hooks = html.slice(html.indexOf("const HOLD_IT_SETTINGS"), html.indexOf("const TIME_IT_SETTINGS"));
const listeners = new Map();
const storage = new Map();
const timers = new Map();
const note = {};
const form = {
  hidden: true,
  elements: {
    rung: { focus() {}, addEventListener: (event, callback) => listeners.set(event, callback) },
    holds: {}, adaptive: {},
  },
  addEventListener: (event, callback) => listeners.set(event, callback),
  querySelector: () => ({ addEventListener: (event, callback) => listeners.set(event, callback) }),
};
let nextId = 0;
let now = 0n;
let sequence = 0n;
const played = [];
let stopped = 0;
let audioClosed = false;
class AudioContext {
  state = "running";
  currentTime = 0;
  createBuffer(channels, frames, rate) {
    assert.equal(channels, 2);
    assert.equal(rate, 22050);
    const waves = Array.from({ length: channels }, () => new Float32Array(frames));
    return { duration: frames / rate, getChannelData: channel => waves[channel] };
  }
  createBufferSource() {
    return {
      connect() {}, disconnect() {},
      start() { played.push(this.buffer); },
      stop() { stopped++; },
    };
  }
  async close() { audioClosed = true; }
}
let host;
host = vm.createContext({
  window: { AudioContext },
  exports: api, framePtr: Number(buffer), FRAME_CAPACITY: Number(capacity), view: bytes, TextDecoder,
  isTaskId: id => id === "hold_it", canvas: { width: 912, height: 684, focus() {} }, screen: "taskhub",
  document: { getElementById: id => id === "hold-it-options" ? form : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  setTimeout(callback) { timers.set(++nextId, callback); return nextId; },
  clearTimeout: id => timers.delete(id),
  apiCreateRun: (id, values, seed) => api.nw_api_v1_create(id, 1n, ...values, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  apiDispatchAction: (handle, action) =>
    api.nw_api_v1_dispatch(handle, 1n, now, sequence++, BigInt(action), 0n, 0n, 0n, 0n, 0n, 0n),
  apiAdvance: handle => api.nw_api_v1_advance(handle, now, 0n, sequence++),
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks, host);
host.openHoldItOptions(true);
assert.equal(form.hidden, false);
assert.equal(form.elements.holds.value, 5);
assert.equal(note.textContent, "Rung 1: within 25%.");
form.elements.rung.value = 13;
form.elements.holds.value = 1;
listeners.get("change")();
assert.ok(note.textContent.includes("clock ticks at the wrong speed"));
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(form.hidden, true);
host.launchTask();
assert.equal(host.holdItInfo(1), 13);
assert.equal(host.holdItInfo(3), 1);
host.holdItAction(2);
assert.equal(timers.size, 1);
now = 25n;
const [[id, tick]] = timers;
timers.delete(id);
tick();
assert.equal(timers.size, 1);
assert.equal(played.length, 1);
const browserRun = host.ensureHoldItRun();
host.destroyHoldItRun();
assert.equal(timers.size, 0);
assert.equal(stopped, 1);
assert.equal(audioClosed, true);
assert.equal(api.nw_api_v1_hold_it_info(browserRun, 0n), -1n);
api.nw_frame_free(buffer);
console.log("PASS: Hold It hub, options preview, private timing, held input, focus loss, and verdict");

const agentCanvas = { width: 96, height: 80 };
const pixels = new Uint8ClampedArray(agentCanvas.width * agentCanvas.height * 4);
const context = {
  canvas: agentCanvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  fillRect() {}, strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {},
  moveTo() {}, lineTo() {}, closePath() {},
  clearRect() { pixels.fill(0); },
  fillText() {
    const color = this.fillStyle === "rgba(64,255,64,1.000)" ? [64, 255, 64, 255] : null;
    if (color) {
      pixels.set(color, pixels.length - 4);
      pixels.set(color, pixels.length - 4 - agentCanvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};
assert.throws(() => createHoldItEnvironment(context, { frameHz: 9 }), /10 frames/);
assert.throws(() => createHoldItEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
const env = createHoldItEnvironment(context, { seed: 17, frameHz: 16, trials: 1 });
assert.equal(env.n_actions, 1);
assert.equal(env.observe().audio_pcm, undefined);
assert.ok(!env.act(1).ok);
for (let tick = 1; tick <= 72; tick++) {
  if (tick > 50) {
    assert.ok(env.act(0).ok);
    assert.ok(!env.act(0).ok);
  }
  const feedback = env.advance();
  assert.equal(feedback.outcome, undefined);
  assert.equal(feedback.audio_rate, 22050);
  assert.equal(feedback.audio_channels, 2);
  assert.equal(feedback.audio_sample_width, 2);
  assert.equal(feedback.audio_pcm.length, 5512);
  if (tick <= 12) assert.equal(feedback.audio_pcm.some(Boolean), false);
  if (tick === 13) assert.equal(feedback.audio_pcm.some(Boolean), true);
}
const verdict = env.advance();
assert.equal(verdict.outcome.scalar, 1);
assert.ok(env.verify(verdict.outcome, verdict));
assert.equal(env.advance().done, true);
assert.equal(env.observe().audio_pcm, undefined);
assert.equal(env.reset(17).frame_seq, 1);
env.close();

const neutral = createHoldItEnvironment(context, { neutralOutcomes: true, runtimePorts: 2 });
assert.ok(neutral.act(1).ok);
assert.equal(neutral.advance().outcome.scalar, 0);
neutral.close();
console.log("PASS: stepped Hold It per-frame hold, elapsed PCM, verified verdict, reset, and cleanup");
