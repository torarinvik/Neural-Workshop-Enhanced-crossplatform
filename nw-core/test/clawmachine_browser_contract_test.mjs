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
  exports, TextDecoder, URLSearchParams, location: { search: "?claw-machine-seed=17" },
  document: { hidden: false, getElementById: id => id === "claw-machine-options" ? form : note },
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
  const isTaskId = id => id === "claw_machine";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyClawMachineRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchLifecycle(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${taskBlock("CLAW_MACHINE")}
`, context);

function tick(dt) {
  now += dt;
  assert.equal(timers.size, 1);
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
}
function key(name) {
  vm.runInContext(`clawMachineKey(CLAW_MACHINE_KEYS.get(${JSON.stringify(name)}));`, context);
}

try {
  assert.match(html, /isClawMachineTask\(\)\) openClawMachineOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isClawMachineTask\(\)\) destroyClawMachineRun\(\);/);
  assert.match(html, /<label>Drops per run/);
  context.openClawMachineOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.equal(note.textContent, "Rung 1: 5 prizes.  A side view.");
  form.elements.rung.value = "13";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateClawMachineOptionsNote();
  assert.equal(note.textContent, "Rung 13: 8 prizes.  The claw swings.");
  listeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.claw-machine.options.v1")), { rung: 13, rounds: 1, adaptive: false });
  assert.equal(vm.runInContext("screen", context), "taskhub");

  vm.runInContext("launchTask();", context);
  key(" ");
  assert.equal(context.clawMachineInfo(0), 1);
  assert.equal(context.clawMachineInfo(1), 13);
  assert.ok(decode(context.clawMachineFrame(true)).some(command => command.text === "rung 13  1/1   40 s"));
  // The page holds Left and A, Right and D, Up and W, Down and S; each is
  // let go on key-up.
  const keys = [["arrowleft", "ArrowLeft", 1], ["a", "a", 2], ["arrowright", "ArrowRight", 4], ["d", "d", 8],
    ["arrowup", "ArrowUp", 16], ["w", "w", 32], ["arrowdown", "ArrowDown", 64], ["s", "s", 128]];
  for (const [name, label, bit] of keys) {
    key(name);
    assert.equal(context.clawMachineInfo(17), bit, name);
    assert.equal(context.releaseClawMachineKey({ key: label, code: label }), true, name);
    assert.equal(context.clawMachineInfo(17), 0, name);
  }
  assert.equal(context.releaseClawMachineKey({ key: "x", code: "KeyX" }), false, "X is not one of its keys");
  // Enter drops; the claw comes down in 1.3 s and closes.
  key("enter");
  assert.equal(context.clawMachineInfo(10), 1);
  for (let i = 0; i < 14; i++) tick(100);
  assert.equal(context.clawMachineInfo(0), 2);
  assert.ok(context.clawMachineInfo(8) >= 2);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("clawMachineRun", context), 0n);
} finally {
  context.destroyClawMachineRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Claw Machine web shell options, eight held keys, Enter's drop, clock, and disposal passed");
