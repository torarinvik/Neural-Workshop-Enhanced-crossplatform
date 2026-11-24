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
  document: { getElementById: id => id === "ferry-options" ? form : note },
  exports, TextDecoder, URLSearchParams, location: { search: "?ferry-seed=17" },
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
  const isTaskId = id => id === "ferry";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyFerryRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchText(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${extract("const FERRY_SETTINGS", "const DOCKING_SETTINGS")}
`, context);

try {
  assert.match(html, /event\.key\.toLowerCase\(\) === "c" && isFerryTask\(\)\) openFerryOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isFerryTask\(\)\) destroyFerryRun\(\);/);
  assert.match(html, /apiDispatchPointer\(handle, API_EVENT\.pointerDown, event\)/);
  context.openFerryOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.match(note.textContent, /Rung 1: 2 crossings, a 1\.0 m\/s river, 0 lane/);

  form.elements.rung.value = "16";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateFerryOptionsNote();
  assert.match(note.textContent, /Fog hides the barges\./);
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(form.hidden, true);
  assert.equal(vm.runInContext("screen", context), "taskhub");
  assert.deepEqual(JSON.parse(settings.get("nw.ferry.options.v1")), { rung: 16, rounds: 1, adaptive: false });

  context.openFerryOptions(true);
  assert.equal(form.elements.rung.value, 16);
  form.elements.rung.value = "25";
  listeners.get("click")();
  assert.equal(JSON.parse(settings.get("nw.ferry.options.v1")).rung, 16);

  vm.runInContext('launchTask(); ferryKey(FERRY_KEYS.get(" "));', context);
  assert.equal(context.ferryInfo(0), 1);
  assert.equal(timers.size, 1);
  const frame = elapsed => {
    now += elapsed;
    const [id, callback] = timers.entries().next().value;
    timers.delete(id);
    callback();
  };
  context.ferryKey(79);
  context.ferryKey(77);
  frame(100);
  assert.equal(context.ferryInfo(14), 95500);
  assert.equal(context.releaseFerryKey({ key: "a", code: "KeyA", preventDefault() {} }), true);
  frame(100);
  assert.equal(context.ferryInfo(14), 95500);
  context.ferryKey(78);
  context.clearFerryControls(9n);
  frame(100);
  assert.equal(context.ferryInfo(14), 95500);
  for (let tick = 0; tick < 2500 && context.ferryInfo(0) === 1; tick++) frame(100);
  assert.equal(context.ferryInfo(0), 2);
  assert.equal(timers.size, 1);
  now += 3000;
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
  assert.equal(context.ferryInfo(0), 3);
  const handle = vm.runInContext("ferryRun", context);
  context.openFerryOptions();
  form.elements.rung.value = "4";
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(vm.runInContext("ferryRun", context), handle);
  assert.equal(context.ferryInfo(0), 0);
  assert.equal(context.ferryInfo(8), 0);
  assert.equal(context.ferryInfo(10), 4);
  context.ferryKey(1);
  assert.equal(timers.size, 1);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("ferryRun", context), 0n);
} finally {
  context.destroyFerryRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Ferry browser shell: options, persistence, held keys, focus cleanup, feedback, and disposal pass");
