import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports } = await instantiateElisa(bytes, { warn: false });
const settings = new Map();
const timers = new Map();
const listeners = new Map();
let now = 0;
let timerId = 0;
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
  exports, TextDecoder, URLSearchParams, location: { search: "?bartender-seed=17" },
  document: { hidden: false, getElementById: id => id === "bartender-options" ? form : note },
  localStorage: { getItem: key => settings.get(key) ?? null, setItem: (key, value) => settings.set(key, value) },
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
function taskBlock(name) {
  const start = html.indexOf(`const ${name}_SETTINGS =`);
  assert.ok(start >= 0);
  const end = /^const [A-Z_]+_SETTINGS =/m.exec(html.slice(start + 1));
  assert.ok(end);
  return html.slice(start, start + 1 + end.index);
}
vm.runInContext(`
  let screen = "taskhub";
  const apiSequences = new Map();
  const apiClockTimes = new Map();
  const isTaskId = id => id === "bartender";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyBartenderRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchKeyUp(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${taskBlock("BARTENDER")}
`, context);

function tick(dt) {
  now += dt;
  assert.equal(timers.size, 1);
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
}

try {
  assert.match(html, /isBartenderTask\(\)\) openBartenderOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isBartenderTask\(\)\) destroyBartenderRun\(\);/);
  context.openBartenderOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.equal(note.textContent, "Rung 1: 1 customers, 2 bottles.");
  form.elements.rung.value = "16";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateBartenderOptionsNote();
  assert.match(note.textContent, /Pour by ear.*Remember the usual/);
  listeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.bartender.options.v1")), { rung: 16, rounds: 1, adaptive: false });
  assert.equal(vm.runInContext("screen", context), "taskhub");

  vm.runInContext('launchTask(); bartenderKey(BARTENDER_KEYS.get("enter"));', context);
  assert.equal(context.bartenderInfo(0), 1);
  assert.ok(decode(context.bartenderFrame(true)).some(command => command.text === "0 of 5 served"));
  vm.runInContext('bartenderKey(BARTENDER_KEYS.get("i"));', context);
  assert.equal(context.bartenderInfo(16), 1);
  tick(50);
  vm.runInContext('bartenderKey(BARTENDER_KEYS.get(" "));', context);
  assert.equal(context.bartenderInfo(16), 0);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("bartenderRun", context), 0n);
} finally {
  context.destroyBartenderRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Bartender web shell options, ice aliases, serving display, and disposal passed");
