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
  document: { getElementById: id => id === "bluff-options" ? form : note },
  exports, TextDecoder, URLSearchParams, location: { search: "?bluff-seed=17" },
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
  const isTaskId = id => id === "bluff";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyBluffRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchKeyUp(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${extract("const BLUFF_SETTINGS", "const BANDIT_SETTINGS")}
`, context);

try {
  assert.match(html, /event\.key\.toLowerCase\(\) === "c" && isBluffTask\(\)\) openBluffOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isBluffTask\(\)\) destroyBluffRun\(\);/);
  assert.match(html, /apiDispatchPointer\(ensureBluffRun\(\), API_EVENT\.pointerDown, event\)/);
  context.openBluffOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.match(note.textContent, /Rung 1: 21 hands/);

  form.elements.rung.value = "18";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateBluffOptionsNote();
  assert.match(note.textContent, /Rung 18:/);
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(form.hidden, true);
  assert.equal(vm.runInContext("screen", context), "taskhub");
  assert.deepEqual(JSON.parse(settings.get("nw.bluff.options.v1")), { rung: 18, rounds: 1, adaptive: false });

  context.openBluffOptions(true);
  assert.equal(form.elements.rung.value, 18);
  form.elements.rung.value = "25";
  listeners.get("click")();
  assert.equal(JSON.parse(settings.get("nw.bluff.options.v1")).rung, 18);

  vm.runInContext('launchTask(); bluffKey(BLUFF_KEYS.get(" "));', context);
  for (let i = 0; i < 200 && context.bluffInfo(0) === 1; i++) {
    vm.runInContext('bluffKey(BLUFF_KEYS.get("c"));', context);
  }
  assert.equal(context.bluffInfo(0), 2);
  assert.equal(timers.size, 1);
  now = 3000;
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
  assert.equal(context.bluffInfo(0), 3);
  const handle = vm.runInContext("bluffRun", context);
  context.openBluffOptions();
  form.elements.rung.value = "3";
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(vm.runInContext("bluffRun", context), handle);
  assert.equal(context.bluffInfo(0), 0);
  assert.equal(context.bluffInfo(8), 3);
  context.bluffKey(1);
  for (let i = 0; i < 200 && context.bluffInfo(0) === 1; i++) context.bluffKey(12);
  assert.equal(timers.size, 1);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("bluffRun", context), 0n);
} finally {
  context.destroyBluffRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Bluff browser shell: options, persistence, keyboard, feedback animation, and disposal pass");
