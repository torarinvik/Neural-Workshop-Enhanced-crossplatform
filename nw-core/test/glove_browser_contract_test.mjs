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
  exports, TextDecoder, URLSearchParams, location: { search: "?glove-seed=17" },
  document: { hidden: false, getElementById: id => id === "glove-options" ? form : note },
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
  const isTaskId = id => id === "glove";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyGloveRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchLifecycle(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${taskBlock("GLOVE")}
`, context);

function tick(dt) {
  now += dt;
  assert.equal(timers.size, 1);
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
}

try {
  assert.match(html, /isGloveTask\(\)\) openGloveOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isGloveTask\(\)\) destroyGloveRun\(\);/);
  assert.match(html, /<label>Innings per run/);
  context.openGloveOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.equal(note.textContent, "Rung 1: 4 pitches at 14 m/s.");
  form.elements.rung.value = "16";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateGloveOptionsNote();
  assert.equal(note.textContent, "Rung 16: 6 pitches at 28 m/s.  A cut about every 0.3 s.");
  listeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.glove.options.v1")), { rung: 16, rounds: 1, adaptive: false });
  assert.equal(vm.runInContext("screen", context), "taskhub");

  vm.runInContext('launchTask(); gloveKey(GLOVE_KEYS.get(" "));', context);
  assert.equal(context.gloveInfo(0), 1);
  assert.equal(context.gloveInfo(1), 16);
  assert.ok(decode(context.gloveFrame(true)).some(command => command.text?.startsWith("rung 16  1/1   pitch 1 of ")));
  // Every key the page maps reaches the controller as its own held bit.
  const keys = [["arrowup", 1], ["w", 2], ["arrowdown", 4], ["s", 8], ["arrowleft", 16], ["a", 32],
    ["arrowright", 64], ["d", 128]];
  for (const [key, bit] of keys) {
    vm.runInContext(`gloveKey(GLOVE_KEYS.get(${JSON.stringify(key)}));`, context);
    assert.equal(context.gloveInfo(15) & bit, bit, key);
  }
  assert.equal(context.gloveInfo(15), 255);
  const before = context.gloveInfo(11);
  tick(100);
  assert.ok(context.gloveInfo(11) !== before, "Up, the first held, moves the glove");
  let left = 255;
  for (const [key, code, bit] of [["ArrowUp", "ArrowUp", 1], ["w", "KeyW", 2], ["ArrowDown", "ArrowDown", 4],
    ["s", "KeyS", 8], ["ArrowLeft", "ArrowLeft", 16], ["a", "KeyA", 32], ["ArrowRight", "ArrowRight", 64], ["d", "KeyD", 128]]) {
    assert.equal(context.releaseGloveKey({ key, code }), true, key);
    left &= ~bit;
    assert.equal(context.gloveInfo(15), left, key);
  }
  // Space only starts: it is not a held key, and does nothing in play.
  assert.equal(context.releaseGloveKey({ key: " ", code: "Space" }), false);
  assert.equal(context.releaseGloveKey({ key: "t", code: "KeyT" }), false);
  vm.runInContext('gloveKey(GLOVE_KEYS.get(" "));', context);
  assert.equal(context.gloveInfo(0), 1);
  tick(100);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("gloveRun", context), 0n);
} finally {
  context.destroyGloveRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Glove web shell options, eight held keys, Space, clock, and disposal passed");
