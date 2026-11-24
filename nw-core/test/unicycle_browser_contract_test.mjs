import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports } = await instantiateElisa(bytes, { warn: false });
const settings = new Map();
const listeners = new Map();
const timers = new Map();
let timerId = 0;
let now = 0;
const form = {
  hidden: true,
  elements: { rung: { focus() {}, addEventListener() {} }, rounds: {}, adaptive: {} },
  addEventListener(type, callback) { listeners.set(type, callback); },
  querySelector() {
    return { addEventListener(type, callback) { listeners.set(type, callback); } };
  },
};
const note = { textContent: "" };
let contactSounds = 0;
class AudioContext {
  state = "running";
  destination = {};
  createBuffer(channels, frames, rate) {
    assert.deepEqual([channels, frames, rate], [2, 17640, 22050]);
    return { getChannelData: () => new Float32Array(frames) };
  }
  createBufferSource() {
    return { connect() {}, stop() {}, start() { contactSounds++; } };
  }
}
const context = vm.createContext({
  window: { AudioContext },
  document: { getElementById: id => id === "unicycle-options" ? form : note },
  exports, TextDecoder, URLSearchParams, location: { search: "?unicycle-seed=17" },
  localStorage: { getItem: key => settings.get(key), setItem: (key, value) => settings.set(key, value) },
  framePtr: exports.nw_frame_alloc(1048576n), FRAME_CAPACITY: 1048576,
  performance: { now: () => now },
  physicalKeyCode: () => 0,
  API_EVENT: { keyDown: 2n, keyUp: 3n, focus: 9n },
  requestAnimationFrame: callback => { timers.set(++timerId, callback); return timerId; },
  cancelAnimationFrame: id => timers.delete(id),
  canvas: { focus() {} },
  draw() {},
});
function extract(start, end) {
  const first = html.indexOf(start);
  const last = html.indexOf(end, first + start.length);
  assert.ok(first >= 0 && last > first);
  return html.slice(first, last);
}
vm.runInContext(`
  let screen = "taskhub";
  const apiSequences = new Map();
  const apiClockTimes = new Map();
  const isTaskId = id => id === "unicycle";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyUnicycleRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchText(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${extract("const UNICYCLE_SETTINGS", "const ROVER_SETTINGS")}
`, context);

try {
  assert.match(html, /event\.key\.toLowerCase\(\) === "c" && isUnicycleTask\(\)\) openUnicycleOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isUnicycleTask\(\)\) destroyUnicycleRun\(\);/);
  assert.match(html, /apiDispatchPointer\(handle, API_EVENT\.pointerDown, event\)/);
  context.openUnicycleOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.match(note.textContent, /Rung 1: 22 m\./);

  form.elements.rung.value = "16";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateUnicycleOptionsNote();
  assert.match(note.textContent, /Ledges\./);
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(form.hidden, true);
  assert.equal(vm.runInContext("screen", context), "taskhub");
  assert.deepEqual(JSON.parse(settings.get("nw.unicycle.options.v1")), { rung: 16, rounds: 1, adaptive: false });

  context.openUnicycleOptions(true);
  assert.equal(form.elements.rung.value, 16);
  form.elements.rung.value = "25";
  listeners.get("click")();
  assert.equal(JSON.parse(settings.get("nw.unicycle.options.v1")).rung, 16);

  context.openUnicycleOptions(true);
  form.elements.rung.value = "1";
  listeners.get("submit")({ preventDefault() {} });
  vm.runInContext('launchTask(); unicycleKey(UNICYCLE_KEYS.get(" "));', context);
  assert.equal(context.unicycleInfo(0), 1);
  assert.equal(timers.size, 1);
  const frame = elapsed => {
    now += elapsed;
    const [id, callback] = timers.entries().next().value;
    timers.delete(id);
    callback();
  };
  context.unicycleKey(77);
  context.unicycleKey(4);
  context.unicycleKey(3);
  assert.equal(context.releaseUnicycleKey({ key: "ArrowUp", code: "ArrowUp", preventDefault() {} }), true);
  frame(25);
  assert.equal(context.unicycleInfo(9), 4);
  context.unicycleKey(5);
  frame(25);
  assert.equal(context.unicycleInfo(9), 0);
  context.clearUnicycleControls(9n);
  frame(25);
  assert.equal(context.unicycleInfo(9), -1);
  for (let tick = 0; tick < 80 && context.unicycleInfo(0) === 1; tick++) frame(25);
  assert.equal(context.unicycleInfo(0), 2);
  assert.equal(contactSounds, 1);
  assert.equal(timers.size, 1);
  frame(2500);
  assert.equal(context.unicycleInfo(0), 3);
  const handle = vm.runInContext("unicycleRun", context);
  context.openUnicycleOptions();
  form.elements.rung.value = "4";
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(vm.runInContext("unicycleRun", context), handle);
  assert.equal(context.unicycleInfo(0), 0);
  assert.equal(context.unicycleInfo(8), 0);
  assert.equal(context.unicycleInfo(6), 4);
  context.unicycleKey(1);
  assert.equal(timers.size, 1);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("unicycleRun", context), 0n);
} finally {
  context.destroyUnicycleRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Unicycle browser shell: options, persistence, held keys, focus cleanup, feedback, and disposal pass");
