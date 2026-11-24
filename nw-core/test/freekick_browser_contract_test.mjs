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
  exports, TextDecoder, URLSearchParams, location: { search: "?free-kick-seed=17" },
  document: { hidden: false, getElementById: id => id === "free-kick-options" ? form : note },
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
  const isTaskId = id => id === "free_kick";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyFreeKickRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchLifecycle(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${taskBlock("FREE_KICK")}
`, context);

function tick(dt) {
  now += dt;
  assert.equal(timers.size, 1);
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
}

try {
  assert.match(html, /isFreeKickTask\(\)\) openFreeKickOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isFreeKickTask\(\)\) destroyFreeKickRun\(\);/);
  assert.match(html, /<label>Kicks per run/);
  context.openFreeKickOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.equal(note.textContent, "Rung 1: a ring of 1.20 m.  The flight is drawn.");
  form.elements.rung.value = "16";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateFreeKickOptionsNote();
  assert.equal(note.textContent, "Rung 16: a ring of 0.37 m.  A wall and a keeper.  Wind.");
  listeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.free-kick.options.v1")), { rung: 16, rounds: 1, adaptive: false });
  assert.equal(vm.runInContext("screen", context), "taskhub");

  vm.runInContext('launchTask(); freeKickKey(FREE_KICK_KEYS.get(" "));', context);
  assert.equal(context.freeKickInfo(0), 1);
  assert.equal(context.freeKickInfo(1), 16);
  assert.ok(decode(context.freeKickFrame(true)).some(command => command.text === "rung 16  1/1"));
  // Every dial key the page maps reaches the controller as its own held bit.
  const keys = [["arrowleft", 1], ["arrowright", 2], ["arrowup", 4], ["arrowdown", 8], ["a", 16], ["d", 32],
    ["w", 64], ["s", 128]];
  for (const [key, bit] of keys) {
    vm.runInContext(`freeKickKey(FREE_KICK_KEYS.get(${JSON.stringify(key)}));`, context);
    assert.equal(context.freeKickInfo(14) & bit, bit, key);
  }
  assert.equal(context.freeKickInfo(14), 255);
  tick(100);
  let left = 255;
  for (const [key, code, bit] of [["ArrowLeft", "ArrowLeft", 1], ["ArrowRight", "ArrowRight", 2], ["ArrowUp", "ArrowUp", 4],
    ["ArrowDown", "ArrowDown", 8], ["a", "KeyA", 16], ["d", "KeyD", 32], ["w", "KeyW", 64], ["s", "KeyS", 128]]) {
    assert.equal(context.releaseFreeKickKey({ key, code }), true, key);
    left &= ~bit;
    assert.equal(context.freeKickInfo(14), left, key);
  }
  // Space is the kick, not a held key: it is not taken on release.
  assert.equal(context.releaseFreeKickKey({ key: " ", code: "Space" }), false);
  assert.equal(context.releaseFreeKickKey({ key: "t", code: "KeyT" }), false);
  assert.equal(context.freeKickInfo(15), 0);
  vm.runInContext('freeKickKey(FREE_KICK_KEYS.get(" "));', context);
  assert.equal(context.freeKickInfo(15), 1, "Space kicks during play");
  tick(100);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("freeKickRun", context), 0n);
} finally {
  context.destroyFreeKickRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("FreeKick web shell options, eight held dial keys, the kick, clock, and disposal passed");
