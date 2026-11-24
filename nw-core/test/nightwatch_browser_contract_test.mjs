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
  exports, TextDecoder, URLSearchParams, location: { search: "?night-watch-seed=17" },
  document: { hidden: false, getElementById: id => id === "night-watch-options" ? form : note },
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
  const isTaskId = id => id === "night_watch";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyNightWatchRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchLifecycle(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${taskBlock("NIGHT_WATCH")}
`, context);

function tick(dt) {
  now += dt;
  assert.equal(timers.size, 1);
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
}

try {
  assert.match(html, /isNightWatchTask\(\)\) openNightWatchOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isNightWatchTask\(\)\) destroyNightWatchRun\(\);/);
  assert.match(html, /<label>Nights per run/);
  context.openNightWatchOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.equal(note.textContent, "Rung 1: 2 thieves, 0 others.");
  form.elements.rung.value = "16";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateNightWatchOptionsNote();
  assert.equal(note.textContent, "Rung 16: 4 thieves, 3 others.  Read the orders: the colours change.");
  listeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.night-watch.options.v1")), { rung: 16, rounds: 1, adaptive: false });
  assert.equal(vm.runInContext("screen", context), "taskhub");

  vm.runInContext('launchTask(); nightWatchKey(NIGHT_WATCH_KEYS.get("enter"));', context);
  assert.equal(context.nightWatchInfo(0), 1);
  assert.equal(context.nightWatchInfo(1), 16);
  assert.ok(decode(context.nightWatchFrame(true)).some(command => command.text === "caught 0 / 4"));
  // Every turning key the page maps reaches the controller as its own held bit.
  for (const [key, bit] of [["arrowleft", 1], ["a", 2], ["arrowright", 4], ["d", 8]]) {
    vm.runInContext(`nightWatchKey(NIGHT_WATCH_KEYS.get(${JSON.stringify(key)}));`, context);
    assert.equal(context.nightWatchInfo(15) & bit, bit, key);
  }
  assert.equal(context.nightWatchInfo(15), 15);
  tick(100);
  for (const [key, code, left] of [["ArrowLeft", "ArrowLeft", 14], ["a", "KeyA", 12], ["ArrowRight", "ArrowRight", 8], ["d", "KeyD", 0]]) {
    assert.equal(context.releaseNightWatchKey({ key, code }), true, key);
    assert.equal(context.nightWatchInfo(15), left, key);
  }
  // Keys that are not turning keys are not taken on release.
  assert.equal(context.releaseNightWatchKey({ key: " ", code: "Space" }), false);
  assert.equal(context.releaseNightWatchKey({ key: "t", code: "KeyT" }), false);
  tick(100);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("nightWatchRun", context), 0n);
} finally {
  context.destroyNightWatchRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Night Watch web shell options, four held turning keys, clock, and disposal passed");
