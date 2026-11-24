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
const context = vm.createContext({
  document: { getElementById: id => id === "sokobanlive-options" ? form : note },
  exports, TextDecoder, URLSearchParams, location: { search: "?sokoban-live-seed=17" },
  localStorage: { getItem: key => settings.get(key), setItem: (key, value) => settings.set(key, value) },
  framePtr: exports.nw_frame_alloc(1048576n), FRAME_CAPACITY: 1048576,
  performance: { now: () => now },
  physicalKeyCode: () => 0,
  API_EVENT: { keyDown: 2n },
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
  const isTaskId = id => id === "sokoban_live";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroySokobanLiveRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchKeyUp(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${extract("const SOKOBANLIVE_SETTINGS", "const KITCHEN_SETTINGS")}
`, context);

try {
  assert.match(html, /event\.key\.toLowerCase\(\) === "c" && isSokobanLiveTask\(\)\) openSokobanLiveOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isSokobanLiveTask\(\)\) destroySokobanLiveRun\(\);/);
  assert.match(html, /apiDispatchPointer\(handle, API_EVENT\.pointerDown, event\)/);
  context.openSokobanLiveOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.match(note.textContent, /Rung 1: 1 crate\(s\), 0 guard\(s\)/);

  form.elements.rung.value = "16";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateSokobanLiveOptionsNote();
  assert.match(note.textContent, /Shutters open and shut/);
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(form.hidden, true);
  assert.equal(vm.runInContext("screen", context), "taskhub");
  assert.deepEqual(JSON.parse(settings.get("nw.sokobanlive.options.v1")), { rung: 16, rounds: 1, adaptive: false });

  context.openSokobanLiveOptions(true);
  assert.equal(form.elements.rung.value, 16);
  form.elements.rung.value = "25";
  listeners.get("click")();
  assert.equal(JSON.parse(settings.get("nw.sokobanlive.options.v1")).rung, 16);

  vm.runInContext('launchTask(); sokobanliveKey(SOKOBANLIVE_KEYS.get(" "));', context);
  assert.equal(context.sokobanliveInfo(0), 1);
  assert.equal(timers.size, 1);
  for (let tick = 0; tick < 2200 && context.sokobanliveInfo(0) === 1; tick++) {
    now += 100;
    const [id, callback] = timers.entries().next().value;
    timers.delete(id);
    callback();
  }
  assert.equal(context.sokobanliveInfo(0), 2);
  assert.equal(timers.size, 1);
  now += 3000;
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
  assert.equal(context.sokobanliveInfo(0), 3);
  const handle = vm.runInContext("sokobanliveRun", context);
  context.openSokobanLiveOptions();
  form.elements.rung.value = "4";
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(vm.runInContext("sokobanliveRun", context), handle);
  assert.equal(context.sokobanliveInfo(0), 0);
  assert.equal(context.sokobanliveInfo(8), 0);
  assert.equal(context.sokobanliveInfo(10), 4);
  context.sokobanliveKey(1);
  assert.equal(timers.size, 1);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("sokobanliveRun", context), 0n);
} finally {
  context.destroySokobanLiveRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Sokoban Live browser shell: options, persistence, keyboard, feedback animation, and disposal pass");
