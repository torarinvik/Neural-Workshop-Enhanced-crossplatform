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
  document: { getElementById: id => id === "docking-options" ? form : note },
  exports, TextDecoder, URLSearchParams, location: { search: "?docking-seed=17" },
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
  const isTaskId = id => id === "docking";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyDockingRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchText(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${extract("const DOCKING_SETTINGS", "const UNICYCLE_SETTINGS")}
`, context);

try {
  assert.match(html, /event\.key\.toLowerCase\(\) === "c" && isDockingTask\(\)\) openDockingOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isDockingTask\(\)\) destroyDockingRun\(\);/);
  assert.match(html, /apiDispatchPointer\(handle, API_EVENT\.pointerDown, event\)/);
  context.openDockingOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.match(note.textContent, /Rung 1: within 0\.35 m, under 0\.50 m\/s/);

  form.elements.rung.value = "16";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateDockingOptionsNote();
  assert.match(note.textContent, /No readouts\./);
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(form.hidden, true);
  assert.equal(vm.runInContext("screen", context), "taskhub");
  assert.deepEqual(JSON.parse(settings.get("nw.docking.options.v1")), { rung: 16, rounds: 1, adaptive: false });

  context.openDockingOptions(true);
  assert.equal(form.elements.rung.value, 16);
  form.elements.rung.value = "25";
  listeners.get("click")();
  assert.equal(JSON.parse(settings.get("nw.docking.options.v1")).rung, 16);

  context.openDockingOptions(true);
  form.elements.rung.value = "1";
  listeners.get("submit")({ preventDefault() {} });
  vm.runInContext('launchTask(); dockingKey(DOCKING_KEYS.get(" "));', context);
  assert.equal(context.dockingInfo(0), 1);
  assert.equal(timers.size, 1);
  const frame = elapsed => {
    now += elapsed;
    const [id, callback] = timers.entries().next().value;
    timers.delete(id);
    callback();
  };
  const fullFuel = context.dockingInfo(11);
  context.dockingKey(81);
  context.dockingKey(77);
  frame(100);
  assert.equal(context.dockingInfo(11), fullFuel - 100);
  assert.equal(context.releaseDockingKey({ key: "a", code: "KeyA", preventDefault() {} }), true);
  frame(100);
  assert.equal(context.dockingInfo(11), fullFuel - 200);
  context.dockingKey(84);
  context.clearDockingControls(9n);
  frame(100);
  assert.equal(context.dockingInfo(11), fullFuel - 200);
  for (let tick = 0; tick < 490 && context.dockingInfo(0) === 1; tick++) frame(100);
  assert.equal(context.dockingInfo(0), 2);
  assert.equal(contactSounds, 1);
  assert.equal(timers.size, 1);
  frame(2500);
  assert.equal(context.dockingInfo(0), 3);
  const handle = vm.runInContext("dockingRun", context);
  context.openDockingOptions();
  form.elements.rung.value = "4";
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(vm.runInContext("dockingRun", context), handle);
  assert.equal(context.dockingInfo(0), 0);
  assert.equal(context.dockingInfo(8), 0);
  assert.equal(context.dockingInfo(6), 4);
  context.dockingKey(1);
  assert.equal(timers.size, 1);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("dockingRun", context), 0n);
} finally {
  context.destroyDockingRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Docking browser shell: options, persistence, held keys, focus cleanup, feedback, and disposal pass");
