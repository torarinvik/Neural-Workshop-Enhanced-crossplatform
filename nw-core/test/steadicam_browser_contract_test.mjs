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
  exports, TextDecoder, URLSearchParams, location: { search: "?steadicam-seed=17" },
  document: { hidden: false, getElementById: id => id === "steadicam-options" ? form : note },
  localStorage: { getItem: key => settings.get(key) ?? null, setItem: (key, value) => settings.set(key, value) },
  framePtr: exports.nw_frame_alloc(1048576n), FRAME_CAPACITY: 1048576,
  performance: { now: () => now },
  physicalKeyCode: () => 0,
  API_EVENT: { keyDown: 2n, keyUp: 3n },
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
  const isTaskId = id => id === "steadicam";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroySteadicamRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchLifecycle(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${taskBlock("STEADICAM")}
`, context);

function tick(dt) {
  now += dt;
  assert.equal(timers.size, 1);
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
}

try {
  assert.match(html, /isSteadicamTask\(\)\) openSteadicamOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isSteadicamTask\(\)\) destroySteadicamRun\(\);/);
  assert.match(html, /<label>Takes per run/);
  context.openSteadicamOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.equal(note.textContent, "Rung 1: 25 s, 80% framed.");
  form.elements.rung.value = "16";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateSteadicamOptionsNote();
  assert.equal(note.textContent, "Rung 16: 40 s, 79% framed.  A heavy head.  Leave lead room.");
  listeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.steadicam.options.v1")), { rung: 16, rounds: 1, adaptive: false });
  assert.equal(vm.runInContext("screen", context), "taskhub");

  vm.runInContext('launchTask(); steadicamKey(STEADICAM_KEYS.get(" "));', context);
  assert.equal(context.steadicamInfo(0), 1);
  assert.equal(context.steadicamInfo(1), 16);
  assert.ok(decode(context.steadicamFrame(true)).some(command => command.text?.startsWith("rung 16  1/1   framed 0% (need 79%)")));
  // Every camera key the page maps reaches the controller as its own held bit.
  const keys = [["arrowleft", 1], ["a", 2], ["arrowright", 4], ["d", 8], ["arrowup", 16], ["w", 32],
    ["arrowdown", 64], ["s", 128], ["e", 256], ["q", 512]];
  for (const [key, bit] of keys) {
    vm.runInContext(`steadicamKey(STEADICAM_KEYS.get(${JSON.stringify(key)}));`, context);
    assert.equal(context.steadicamInfo(14) & bit, bit, key);
  }
  assert.equal(context.steadicamInfo(14), 1023);
  tick(100);
  let left = 1023;
  for (const [key, code, bit] of [["ArrowLeft", "ArrowLeft", 1], ["a", "KeyA", 2], ["ArrowRight", "ArrowRight", 4],
    ["d", "KeyD", 8], ["ArrowUp", "ArrowUp", 16], ["w", "KeyW", 32], ["ArrowDown", "ArrowDown", 64],
    ["s", "KeyS", 128], ["e", "KeyE", 256], ["q", "KeyQ", 512]]) {
    assert.equal(context.releaseSteadicamKey({ key, code }), true, key);
    left &= ~bit;
    assert.equal(context.steadicamInfo(14), left, key);
  }
  // Keys that are not camera keys are not taken on release.
  assert.equal(context.releaseSteadicamKey({ key: " ", code: "Space" }), false);
  assert.equal(context.releaseSteadicamKey({ key: "t", code: "KeyT" }), false);
  // The page's wheel listener sends the wheel to the run.
  assert.match(html, /isSteadicamTask\(\) && steadicamRun && steadicamOptionsForm\.hidden\) \{\n    if \(apiDispatchWheel\(steadicamRun, event\) === 1n\)/);
  tick(100);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("steadicamRun", context), 0n);
} finally {
  context.destroySteadicamRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Steadicam web shell options, ten held camera keys, clock, and disposal passed");
