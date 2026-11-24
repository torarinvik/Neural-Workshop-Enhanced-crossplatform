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
  exports, TextDecoder, URLSearchParams, location: { search: "?shadow-puppets-seed=17" },
  document: { hidden: false, getElementById: id => id === "shadow-puppets-options" ? form : note },
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
  const isTaskId = id => id === "shadow_puppets";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyShadowPuppetsRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchLifecycle(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${taskBlock("SHADOW_PUPPETS")}
`, context);

function tick(dt) {
  now += dt;
  assert.equal(timers.size, 1);
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
}

try {
  assert.match(html, /isShadowPuppetsTask\(\)\) openShadowPuppetsOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isShadowPuppetsTask\(\)\) destroyShadowPuppetsRun\(\);/);
  assert.match(html, /<label>Figures per run/);
  context.openShadowPuppetsOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.equal(note.textContent, "Rung 1: 1 shadows, within 16 degrees.");
  form.elements.rung.value = "16";
  context.updateShadowPuppetsOptionsNote();
  assert.equal(note.textContent, "Rung 16: 2 shadows, within 11 degrees.  The figure is hidden.");
  form.elements.rung.value = "4";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  listeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.shadow-puppets.options.v1")), { rung: 4, rounds: 1, adaptive: false });
  assert.equal(vm.runInContext("screen", context), "taskhub");

  vm.runInContext('launchTask(); shadowPuppetsKey(SHADOW_PUPPETS_KEYS.get("enter"));', context);
  assert.equal(context.shadowPuppetsInfo(0), 1);
  assert.equal(context.shadowPuppetsInfo(1), 4);
  assert.ok(decode(context.shadowPuppetsFrame(true)).some(command => command.text === "Cast the shadow shown"));
  // Both roll keys the page maps reach the controller as their own held bit,
  // and a held key turns the figure on the page's own clock.
  const still = context.shadowPuppetsInfo(15);
  for (const [key, bit] of [["q", 1], ["e", 2]]) {
    vm.runInContext(`shadowPuppetsKey(SHADOW_PUPPETS_KEYS.get(${JSON.stringify(key)}));`, context);
    assert.equal(context.shadowPuppetsInfo(14) & bit, bit, key);
  }
  assert.equal(context.shadowPuppetsInfo(14), 3);
  tick(100);
  assert.notEqual(context.shadowPuppetsInfo(15), still, "a held Q turned nothing");
  for (const [key, code, left] of [["Q", "KeyQ", 2], ["e", "KeyE", 0]]) {
    assert.equal(context.releaseShadowPuppetsKey({ key, code }), true, key);
    assert.equal(context.shadowPuppetsInfo(14), left, key);
  }
  // Keys that are not roll keys are not taken on release.
  assert.equal(context.releaseShadowPuppetsKey({ key: " ", code: "Space" }), false);
  assert.equal(context.releaseShadowPuppetsKey({ key: "a", code: "KeyA" }), false);
  tick(100);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("shadowPuppetsRun", context), 0n);
} finally {
  context.destroyShadowPuppetsRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Shadow Puppets web shell options, two held roll keys, clock, and disposal passed");
