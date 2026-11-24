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
  exports, TextDecoder, URLSearchParams, location: { search: "?semaphore-seed=17" },
  document: { hidden: false, getElementById: id => id === "semaphore-options" ? form : note },
  localStorage: { getItem: key => settings.get(key) ?? null, setItem: (key, value) => settings.set(key, value) },
  framePtr: exports.nw_frame_alloc(1048576n), FRAME_CAPACITY: 1048576,
  performance: { now: () => now },
  physicalKeyCode: () => 0,
  API_EVENT: { action: 1n, keyDown: 2n, keyUp: 3n, pointerMove: 4n, pointerDown: 5n, pointerUp: 6n,
    wheel: 7n, text: 8n, focus: 9n, visibility: 10n, cancel: 11n },
  requestAnimationFrame: callback => { timers.set(++timerId, callback); return timerId; },
  cancelAnimationFrame: id => timers.delete(id),
  canvas: { width: 912, height: 684, focus() {} },
  draw() {},
});

function extract(start, end) {
  const first = html.indexOf(start);
  const last = html.indexOf(end, first + start.length);
  assert.ok(first >= 0 && last > first, start);
  return html.slice(first, last);
}
function taskBlock(name) {
  const start = html.indexOf(`const ${name}_SETTINGS =`);
  assert.ok(start >= 0);
  const end = /^const [A-Z_]+_SETTINGS =/m.exec(html.slice(start + 1));
  assert.ok(end);
  return html.slice(start, start + 1 + end.index);
}
// The page's own in-task keydown branch for Semaphore, run as a function.
const keydown = extract("    if (isSemaphoreTask()) {\n      if (!semaphoreOptionsForm.hidden || event.metaKey",
  "    if (isCipherAbyssTask()) {");
vm.runInContext(`
  let screen = "taskhub";
  const apiSequences = new Map();
  const apiClockTimes = new Map();
  const isTaskId = id => id === "semaphore";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroySemaphoreRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchLifecycle(")}
  ${extract("function apiDispatchLifecycle(", "function apiDispatchPointer(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${taskBlock("SEMAPHORE")}
  function semaphoreKeydown(event) {
${keydown}
  }
`, context);

function tick(dt) {
  now += dt;
  assert.equal(timers.size, 1);
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
}
function press(key, extra = {}) {
  let prevented = false;
  context.semaphoreKeydown({ key, repeat: false, metaKey: false, ctrlKey: false, altKey: false,
    preventDefault() { prevented = true; }, ...extra });
  return prevented;
}

try {
  assert.match(html, /isSemaphoreTask\(\)\) openSemaphoreOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isSemaphoreTask\(\)\) destroySemaphoreRun\(\);/);
  assert.match(html, /<label>Messages per run/);
  context.openSemaphoreOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.equal(note.textContent, "Rung 1: 4 letters, 10.0 seconds each.");
  form.elements.rung.value = "25";
  context.updateSemaphoreOptionsNote();
  assert.equal(note.textContent, "Rung 25: 8 letters, 4.7 seconds each.  The signaller sometimes turns their back.  No chart.");
  form.elements.rung.value = "1";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  listeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.semaphore.options.v1")), { rung: 1, rounds: 1, adaptive: false });
  assert.equal(vm.runInContext("screen", context), "taskhub");

  // At the ready screen C opens the options; a letter is not taken.
  vm.runInContext("launchTask();", context);
  assert.equal(press("c"), true);
  assert.equal(form.hidden, false);
  listeners.get("submit")({ preventDefault() {} });
  vm.runInContext("launchTask();", context);
  assert.equal(press("q"), false);
  assert.equal(context.semaphoreInfo(0), 0);

  assert.equal(press("Enter"), true);
  assert.equal(context.semaphoreInfo(0), 1);
  assert.equal(context.semaphoreInfo(1), 1);
  assert.ok(decode(context.semaphoreFrame(true)).some(command => command.text === "Copy each signal with your flags and type its letter"));
  for (let i = 0; i < 400 && context.semaphoreInfo(15) < 0; i++) tick(16);
  assert.ok(context.semaphoreInfo(15) >= 0, "no signal came up");
  // During play C is a letter, not the options key; shifted letters count;
  // digits, repeats and modified keys are not letters.
  assert.equal(press("1"), false);
  assert.equal(press("q", { repeat: true }), true);
  assert.equal(press("q", { metaKey: true }), false);
  assert.equal(context.semaphoreInfo(12), 0);
  assert.equal(press("C"), true);
  assert.equal(form.hidden, true, "C during play must not open the options");
  assert.equal(context.semaphoreInfo(12), 1, "the typed letter reached the run as a mismatch");
  tick(16);
  assert.equal(press("Escape"), true);
  assert.equal(vm.runInContext("screen", context), "taskhub");
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("semaphoreRun", context), 0n);
} finally {
  context.destroySemaphoreRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Semaphore web shell options, C at ready, Enter start, typed letters, clock, Escape, and disposal passed");
