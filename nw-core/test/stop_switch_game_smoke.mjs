import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const { exports: api, instance, createStopAndSwitchEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_stop_switch();
assert.equal(task, 1769824260n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const create = (rung, blocks, adaptive = 1n, stepped = 0n) =>
  api.nw_api_v1_create(task, 1n, rung, blocks, adaptive, stepped, 0n, 0n, 0n);
assert.equal(create(2n, 1n), -3n);
assert.equal(create(1n, 2n), -3n);
assert.equal(create(1n, 1n, 2n), -3n);
const custom = create(2n, 2n, 1n, 1n);
assert.ok(custom > 0n);
assert.equal(api.nw_api_v1_destroy(custom), 0n);

const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
let run = create(25n, 1n);
let sequence = 0n;
const event = (kind, at, code, x = 0n, y = 0n) =>
  api.nw_api_v1_dispatch(run, kind, BigInt(at), sequence++, code, 0n, 0n, 0n, x, y, 0n);
const pointer = at => event(5n, at, 0n, 500000n, 500000n);
const advance = at => api.nw_api_v1_advance(run, BigInt(at), 0n, sequence++);
const info = field => api.nw_api_v1_stop_switch_info(run, BigInt(field));
const state = () => {
  assert.equal(api.nw_api_v1_read_state(run, buffer, capacity), 112n);
  const view = new DataView(instance.exports.memory.buffer, Number(buffer), 112);
  assert.equal(view.getUint32(8, true), Number(task));
  return Array.from({ length: 12 }, (_, field) => view.getBigInt64(16 + field * 8, true));
};
const frame = () => {
  const length = api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n);
  assert.ok(length > 0n);
  return decode(new Uint8Array(instance.exports.memory.buffer, Number(buffer), Number(length)));
};
const hasText = text => frame().some(command => command.kind === Kind.TEXT && command.text === text);
const hasRing = () => frame().some(command => command.kind === Kind.LINE && command.color === 0xdc2828ff);

// Seed zero at rung 25: first an opposite-rule orange circle on the left,
// then an opposite-rule blue square on the right with a 300 ms stop delay.
assert.ok(hasText("Press Space or click to start"));
assert.equal(pointer(0), 1n);
assert.deepEqual(state().slice(7), [0n, 0n, -1n, -1n, -1n]);
assert.equal(info(12), -1n);
assert.ok(!hasText("OPPOSITE"));
assert.equal(advance(599), 2n);
assert.equal(advance(600), 1n);
assert.deepEqual(state().slice(7), [1n, 0n, 2n, 0n, 1n]);
assert.ok(hasText("OPPOSITE"));
assert.equal(pointer(650), 2n);
assert.equal(event(2n, 700, 5n), 1n);
assert.equal(info(5), 1n);
assert.deepEqual(state().slice(7), [0n, 0n, -1n, -1n, -1n]);
assert.equal(advance(1300), 1n);
assert.deepEqual(state().slice(7), [1n, 0n, 2n, 1n, 0n]);
assert.equal(info(12), 1n);
assert.equal(advance(1599), 2n);
assert.ok(!hasRing());
assert.equal(advance(1601), 1n);
assert.equal(info(8), 1n);
assert.ok(hasRing());
assert.equal(advance(1900), 1n);
assert.equal(info(5), 2n);
assert.equal(info(8), 0n);
assert.equal(api.nw_api_v1_destroy(run), 0n);

run = create(1n, 1n);
sequence = 0n;
assert.equal(event(2n, 0, 1n), 1n);
assert.deepEqual(state().slice(9), [0n, -1n, -1n]);
assert.ok(hasText("SHAPE"));
for (let stimulus = 0; stimulus < 12; stimulus++) {
  const onset = 601 + stimulus * 700;
  assert.equal(advance(onset), 1n);
  const key = info(10) === 0n ? 3n : 5n;
  assert.equal(event(2n, onset + 99, key), 1n);
}
assert.equal(info(0), 2n);
assert.equal(info(5), 12n);
assert.equal(info(14), 1n);
assert.equal(info(15), 1n);
assert.deepEqual(state().slice(9), [-1n, -1n, -1n]);
assert.ok(hasText("12 of 12 right (11 needed)"));
const deadline = info(16);
assert.equal(advance(deadline - 1n), 2n);
assert.equal(advance(deadline), 1n);
assert.ok(hasText("1 of 1 passed   highest rung passed 1"));
assert.equal(api.nw_api_v1_destroy(run), 0n);
assert.equal(info(0), -1n);
assert.deepEqual(TASK_IDS_BY_CATEGORY[6], ["cookie_thief", "stop_and_switch", "delay", "hold_it", "morning_round"]);
const bytes = length => new Uint8Array(instance.exports.memory.buffer, Number(buffer), length);
const hubLength = api.nw_taskhub_write(buffer, capacity, 6n, 1n, 0n, 912n, 684n);
assert.ok(hubLength > 0n);
const cards = decode(bytes(Number(hubLength))).map(command => command.text)
  .filter(label => ["Cookie Thief", "Stop & Switch", "Delay"].includes(label));
assert.deepEqual(cards, ["Cookie Thief", "Stop & Switch", "Delay"]);

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const STOP_SWITCH_SETTINGS"), html.indexOf("const DELAY_SETTINGS"));
const keyBranch = html.slice(html.indexOf('    if (isStopSwitchTask()) {\n      const key'),
  html.indexOf('    if (isDelayTask()) {\n      const key'));
const listeners = new Map();
const note = {};
const options = {
  hidden: true,
  elements: {
    rung: { focus() {}, addEventListener: (event, callback) => listeners.set(event, callback) },
    blocks: {}, adaptive: {},
  },
  addEventListener: (event, callback) => listeners.set(event, callback),
  querySelector: () => ({ addEventListener: (event, callback) => listeners.set(event, callback) }),
};
const storage = new Map();
const timers = new Map();
let timerId = 0;
let now = 0n;
const host = vm.createContext({
  exports: api, framePtr: Number(buffer), FRAME_CAPACITY: Number(capacity), view: bytes, TextDecoder,
  screen: "taskhub", canvas: { width: 912, height: 684, focus() {} },
  document: { getElementById: id => id === "stop-switch-options" ? options : note },
  localStorage: { getItem: key => storage.get(key), setItem: (key, value) => storage.set(key, value) },
  isTaskId: id => id === "stop_and_switch",
  draw() {},
  setTimeout(callback) { timers.set(++timerId, callback); return timerId; },
  clearTimeout: id => timers.delete(id),
  apiCreateRun: (id, values, seed) => api.nw_api_v1_create(id, 1n, ...values, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  apiDispatchAction: (handle, action) =>
    api.nw_api_v1_dispatch(handle, 1n, now, sequence++, BigInt(action), 0n, 0n, 0n, 0n, 0n, 0n),
  apiAdvance: handle => api.nw_api_v1_advance(handle, now, 0n, sequence++),
});
host.launchTask = () => { host.screen = "task"; };
host.setScreen = screen => {
  if (host.screen === "task" && screen === "taskhub") host.destroyStopSwitchRun();
  host.screen = screen;
};
vm.runInContext(hooks + "\nfunction key(event) {\n" + keyBranch + "\n}", host);
const key = value => {
  let prevented = false;
  host.key({ key: value, preventDefault() { prevented = true; } });
  assert.ok(prevented);
};
host.openStopSwitchOptions(true);
assert.equal(options.hidden, false);
assert.equal(options.elements.blocks.value, 6);
assert.equal(note.textContent, "Rung 1: 12 stimuli, 1.50 s to answer, 85% right needed.");
options.elements.rung.value = 25;
options.elements.blocks.value = 1;
options.elements.adaptive.checked = false;
listeners.get("change")();
assert.match(note.textContent, /Stops on 30%, 0\.30 s in\.  Rules shape\/colour\/opposite, changing at random\./);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
assert.equal(options.hidden, true);
host.launchTask();
assert.equal(host.stopSwitchInfo(1), 25);
assert.equal(host.stopSwitchInfo(3), 1);
key(" ");
assert.equal(host.stopSwitchInfo(0), 1);
now = 601n;
assert.equal(timers.size, 1);
const [[scheduled, tick]] = timers;
timers.delete(scheduled);
tick();
assert.equal(host.stopSwitchInfo(7), 1);
assert.ok(decode(host.stopSwitchFrame(false)).some(command => command.text === "F"));
const browserRun = host.ensureStopSwitchRun();
key("f");
assert.equal(host.stopSwitchInfo(4), 1);
key("Escape");
assert.equal(host.screen, "taskhub");
assert.equal(timers.size, 0);
assert.equal(api.nw_api_v1_stop_switch_info(browserRun, 0n), -1n);
api.nw_frame_free(buffer);
console.log("PASS: Stop & Switch WASM options, cue visibility, delayed ring, inhibition, and verdict");
console.log("PASS: Stop & Switch browser menu, options persistence, timed input, and cleanup");

const stepped = create(1n, 2n, 1n, 1n);
assert.ok(stepped > 0n);
const agentEvent = (seconds, port) => api.nw_stop_switch_agent_event(stepped, seconds, BigInt(port));
const steppedInfo = field => api.nw_api_v1_stop_switch_info(stepped, BigInt(field));
assert.equal(agentEvent(0, 2), 1n);
assert.equal(agentEvent(-0.01, -1), 2n);
assert.equal(agentEvent(0, 0), 2n);
let seconds = 0;
for (let stimulus = 0; stimulus < 12; stimulus++) {
  seconds += 0.601;
  assert.equal(agentEvent(seconds, -1), 1n);
  assert.equal(steppedInfo(7), 1n);
  assert.equal(agentEvent(seconds, Number(steppedInfo(10))), 1n);
}
assert.equal(steppedInfo(0), 2n);
assert.equal(steppedInfo(5), 12n);
assert.equal(steppedInfo(14), 1n);
assert.equal(agentEvent(seconds + 0.05, -1), 1n);
assert.equal(steppedInfo(0), 2n, "an answer-triggered verdict gets its own publication");
assert.equal(agentEvent(seconds + 0.10, -1), 1n);
assert.deepEqual([steppedInfo(0), steppedInfo(1), steppedInfo(2)], [1n, 2n, 2n]);
assert.equal(api.nw_api_v1_destroy(stepped), 0n);

const agentCanvas = { width: 96, height: 80 };
const pixels = new Uint8ClampedArray(agentCanvas.width * agentCanvas.height * 4);
const context = {
  canvas: agentCanvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  fillRect() {}, strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {},
  moveTo() {}, lineTo() {}, closePath() {},
  clearRect() { pixels.fill(0); },
  fillText() {
    if (this.fillStyle === "rgba(255,64,64,1.000)") {
      pixels.set([255, 64, 64, 255], pixels.length - 4);
      pixels.set([255, 64, 64, 255], pixels.length - 4 - agentCanvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};
assert.throws(() => createStopAndSwitchEnvironment(context, { frameHz: 9 }), /10 frames/);
assert.throws(() => createStopAndSwitchEnvironment(context, { thinkSeconds: 1 }), /already clocked/);
const env = createStopAndSwitchEnvironment(context, { seed: 17, trials: 1, frameHz: 16 });
assert.equal(env.n_actions, 2);
assert.ok(env.act(0).ok, "the Python wrapper finalizes a receipt during the inter-stimulus gap");
assert.ok(!env.act(1).ok);
let reward;
let feedback;
for (let tick = 1; tick <= 450; tick++) {
  [feedback] = env.step();
  if (feedback.outcome) {
    assert.equal(reward, undefined);
    reward = feedback;
  }
  if (feedback.done) {
    assert.equal(tick, 409, "12 missed windows, then one verdict publication");
    break;
  }
}
assert.equal(feedback.done, true);
assert.equal(reward.outcome.scalar, -1);
assert.equal(reward.frame_seq + 1, feedback.frame_seq);
assert.ok(env.verify(reward.outcome, reward));
assert.equal(env.accounting.snapshot().unique_public_outcome_bits, 1);
assert.equal(env.reset(17).frame_seq, 1);
env.close();

const neutral = createStopAndSwitchEnvironment(context, { frameHz: 16, neutralOutcomes: true, runtimePorts: 4 });
assert.ok(neutral.act(3).ok);
const quiet = neutral.advance();
assert.equal(quiet.outcome.scalar, 0);
assert.ok(neutral.verify(quiet.outcome, quiet));
neutral.close();
console.log("PASS: stepped Stop & Switch clock, answered and missed verdicts, receipts, and reset");
