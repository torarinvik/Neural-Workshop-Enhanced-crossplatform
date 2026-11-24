import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode } from "../shells/web/display-list.js";
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
  document: { getElementById: id => id === "dispatch-options" ? form : note },
  exports, TextDecoder, URLSearchParams, location: { search: "?dispatch-seed=17" },
  localStorage: { getItem: key => settings.get(key), setItem: (key, value) => settings.set(key, value) },
  framePtr: exports.nw_frame_alloc(1048576n), FRAME_CAPACITY: 1048576,
  performance: { now: () => now },
  physicalKeyCode: () => 0,
  API_EVENT: { keyDown: 2n },
  requestAnimationFrame: callback => { timers.set(++timerId, callback); return timerId; },
  cancelAnimationFrame: id => timers.delete(id),
  canvas: { width: 912, height: 684, focus() {} },
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
  const isTaskId = id => id === "dispatch";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyDispatchRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchKeyUp(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${extract("const DISPATCH_SETTINGS", "const TUNER_SETTINGS")}
`, context);

try {
  assert.match(html, /event\.key\.toLowerCase\(\) === "c" && isDispatchTask\(\)\) openDispatchOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isDispatchTask\(\)\) destroyDispatchRun\(\);/);
  assert.match(html, /apiDispatchPointer\(ensureDispatchRun\(\), API_EVENT\.pointerDown, event\)/);
  context.openDispatchOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 3);
  assert.match(note.textContent, /Rung 1: 2 crews, bursts of up to 1/);

  form.elements.rung.value = "8";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateDispatchOptionsNote();
  assert.match(note.textContent, /12 seconds at a station for a refit/);
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(form.hidden, true);
  assert.equal(vm.runInContext("screen", context), "taskhub");
  assert.deepEqual(JSON.parse(settings.get("nw.dispatch.options.v1")), { rung: 8, rounds: 1, adaptive: false });

  context.openDispatchOptions(true);
  assert.equal(form.elements.rung.value, 8);
  form.elements.rung.value = "25";
  listeners.get("click")();
  assert.equal(JSON.parse(settings.get("nw.dispatch.options.v1")).rung, 8);

  vm.runInContext('launchTask();', context);
  now = 12000; // Time spent on the ready screen must not age the world.
  vm.runInContext('dispatchKey(DISPATCH_KEYS.get(" ")); dispatchKey(DISPATCH_KEYS.get("1"));', context);
  assert.equal(context.dispatchInfo(4), 0);
  vm.runInContext('dispatchKey(DISPATCH_KEYS.get("j"), { shiftKey: true });', context);
  assert.equal(context.dispatchInfo(4), -1);
  assert.equal(timers.size, 1);
  function tick(elapsed) {
    now += elapsed;
    const [id, callback] = timers.entries().next().value;
    timers.delete(id);
    callback();
  }
  assert.equal(vm.runInContext('apiClockTimes.get(dispatchRun)', context), now);
  tick(10);
  assert.equal(context.dispatchInfo(6), 0);
  for (let i = 0; i < 52; i++) tick(250);
  assert.ok(decode(context.dispatchFrame(0)).some(command => command.text?.endsWith("refits 1/3")));
  assert.equal(context.dispatchInfo(0), 1);
  assert.equal(timers.size, 1);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("dispatchRun", context), 0n);
} finally {
  context.destroyDispatchRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Dispatch browser shell: options, persistence, keyboard refits, active clock, and disposal pass");
