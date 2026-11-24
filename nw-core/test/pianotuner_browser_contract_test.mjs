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
  exports, TextDecoder, URLSearchParams, location: { search: "?piano-tuner-seed=17" },
  document: { hidden: false, getElementById: id => id === "piano-tuner-options" ? form : note },
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
  const isTaskId = id => id === "piano_tuner";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyPianoTunerRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchLifecycle(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${taskBlock("PIANO_TUNER")}
`, context);

function tick(dt) {
  now += dt;
  assert.equal(timers.size, 1);
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
}
function key(name) {
  vm.runInContext(`pianoTunerKey(PIANO_TUNER_KEYS.get(${JSON.stringify(name)}));`, context);
}

try {
  assert.match(html, /isPianoTunerTask\(\)\) openPianoTunerOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isPianoTunerTask\(\)\) destroyPianoTunerRun\(\);/);
  assert.match(html, /<label>Strings per run/);
  context.openPianoTunerOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.equal(note.textContent, "Rung 1: unison, within 20.0 cents.");
  form.elements.rung.value = "10";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updatePianoTunerOptionsNote();
  assert.equal(note.textContent, "Rung 10: unison, octave, fifth, within 5.0 cents.");
  listeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.piano-tuner.options.v1")), { rung: 10, rounds: 1, adaptive: false });
  assert.equal(vm.runInContext("screen", context), "taskhub");

  vm.runInContext("launchTask();", context);
  key(" ");
  assert.equal(context.pianoTunerInfo(0), 1);
  assert.equal(context.pianoTunerInfo(1), 10);
  assert.ok(decode(context.pianoTunerFrame(true)).some(command => command.text === "rung 10  1/1   within 5.0 cents"));
  // The page holds Up and W, Down and S, and Shift; each is let go on key-up.
  const keys = [["arrowup", "ArrowUp", 1], ["w", "w", 2], ["arrowdown", "ArrowDown", 4], ["s", "s", 8], ["shift", "Shift", 16]];
  for (const [name, label, bit] of keys) {
    key(name);
    assert.equal(context.pianoTunerInfo(15), bit, name);
    assert.equal(context.releasePianoTunerKey({ key: label, code: label }), true, name);
    assert.equal(context.pianoTunerInfo(15), 0, name);
  }
  assert.equal(context.releasePianoTunerKey({ key: "a", code: "KeyA" }), false, "A is not one of its keys");
  // Up held for 0.5 s turns the pin 30 cents.
  const before = context.pianoTunerInfo(13);
  key("arrowup");
  for (let i = 0; i < 5; i++) tick(100);
  assert.ok(Math.abs(context.pianoTunerInfo(13) - before - 30000) < 2, String(context.pianoTunerInfo(13) - before));
  context.releasePianoTunerKey({ key: "ArrowUp", code: "ArrowUp" });
  // Enter says done: far out of tune, the try is judged.
  key("enter");
  tick(100);
  assert.equal(context.pianoTunerInfo(0), 2);
  assert.ok([2, 3].includes(context.pianoTunerInfo(8)));
  key(" ");
  assert.equal(context.pianoTunerInfo(0), 2, "Space does nothing while judged");
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("pianoTunerRun", context), 0n);
} finally {
  context.destroyPianoTunerRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Piano Tuner web shell options, five held keys, Enter, clock, and disposal passed");
