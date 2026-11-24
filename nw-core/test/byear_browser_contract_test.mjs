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
  exports, TextDecoder, URLSearchParams, location: { search: "?by-ear-seed=17" },
  document: { hidden: false, getElementById: id => id === "by-ear-options" ? form : note },
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
  const isTaskId = id => id === "by_ear";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyByEarRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchLifecycle(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${taskBlock("BY_EAR")}
`, context);

function tick(dt) {
  now += dt;
  assert.equal(timers.size, 1);
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
}

try {
  assert.match(html, /isByEarTask\(\)\) openByEarOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isByEarTask\(\)\) destroyByEarRun\(\);/);
  assert.match(html, /<label>Melodies per run/);
  context.openByEarOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.equal(note.textContent, "Rung 1: 2 notes.");
  form.elements.rung.value = "13";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateByEarOptionsNote();
  assert.equal(note.textContent, "Rung 13: 7 notes.  Play it from the lit key.  Some notes come in pairs.");
  listeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.by-ear.options.v1")), { rung: 13, rounds: 1, adaptive: false });
  assert.equal(vm.runInContext("screen", context), "taskhub");

  vm.runInContext('launchTask(); byEarKey(BY_EAR_KEYS.get(" "));', context);
  assert.equal(context.byEarInfo(0), 1);
  assert.equal(context.byEarInfo(1), 13);
  assert.ok(decode(context.byEarFrame(true)).some(command => command.text === "rung 13  1/1   7 notes"));
  // The page maps A W S E D F T G Y H U J K to the keys from C to C. While
  // the tune plays every one of them is refused; none is a held key.
  const letters = ["a", "w", "s", "e", "d", "f", "t", "g", "y", "h", "u", "j", "k"];
  assert.deepEqual(letters.map(key => vm.runInContext(`BY_EAR_KEYS.get(${JSON.stringify(key)})`, context)),
    letters.map((_, k) => 103 + k));
  for (const key of letters) {
    vm.runInContext(`byEarKey(BY_EAR_KEYS.get(${JSON.stringify(key)}));`, context);
    assert.equal(context.releaseByEarKey({ key, code: `Key${key.toUpperCase()}` }), false, key);
  }
  assert.equal(context.byEarInfo(15), 0, "nothing is pressed while the tune plays");
  // 4.075 s of tune: then G#, the lit key, is the first of the tune.
  for (let i = 0; i < 45; i++) tick(100);
  assert.equal(context.byEarInfo(14), 0);
  vm.runInContext('byEarKey(BY_EAR_KEYS.get("y"));', context);
  assert.deepEqual([context.byEarInfo(10), context.byEarInfo(15)], [1, 1]);
  vm.runInContext('byEarKey(BY_EAR_KEYS.get(" "));', context);
  assert.equal(context.byEarInfo(0), 1, "Space does nothing in play");
  tick(100);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("byEarRun", context), 0n);
} finally {
  context.destroyByEarRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("By Ear web shell options, thirteen keys, the tune heard first, Space, clock, and disposal passed");
