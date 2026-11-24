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
  exports, TextDecoder, URLSearchParams, location: { search: "?cricket-hunt-seed=17" },
  document: { hidden: false, getElementById: id => id === "cricket-hunt-options" ? form : note },
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
  const isTaskId = id => id === "cricket_hunt";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyCricketHuntRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchLifecycle(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${taskBlock("CRICKET_HUNT")}
`, context);

function tick(dt) {
  now += dt;
  assert.equal(timers.size, 1);
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
}
function key(name) {
  vm.runInContext(`cricketHuntKey(CRICKET_HUNT_KEYS.get(${JSON.stringify(name)}));`, context);
}

try {
  assert.match(html, /isCricketHuntTask\(\)\) openCricketHuntOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isCricketHuntTask\(\)\) destroyCricketHuntRun\(\);/);
  assert.match(html, /<label>Hunts per run/);
  context.openCricketHuntOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.equal(note.textContent, "Rung 1: 1 cricket(s).");
  form.elements.rung.value = "10";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateCricketHuntOptionsNote();
  assert.equal(note.textContent, "Rung 10: 3 cricket(s).  They hop.");
  listeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.cricket-hunt.options.v1")), { rung: 10, rounds: 1, adaptive: false });
  assert.equal(vm.runInContext("screen", context), "taskhub");

  vm.runInContext("launchTask();", context);
  key(" ");
  assert.equal(context.cricketHuntInfo(0), 1);
  assert.equal(context.cricketHuntInfo(1), 10);
  assert.ok(decode(context.cricketHuntFrame(true)).some(command => command.text === "rung 10  1/1   caught 0 of 3   grabs left 3"));
  // The page holds W and Up, S and Down, A and Left, D and Right, Q and E;
  // each is let go on key-up.
  const keys = [["w", "w", 1], ["arrowup", "ArrowUp", 2], ["s", "s", 4], ["arrowdown", "ArrowDown", 8], ["a", "a", 16],
    ["arrowleft", "ArrowLeft", 32], ["d", "d", 64], ["arrowright", "ArrowRight", 128], ["q", "q", 256], ["e", "e", 512]];
  for (const [name, label, bit] of keys) {
    key(name);
    assert.equal(context.cricketHuntInfo(17), bit, name);
    assert.equal(context.releaseCricketHuntKey({ key: label, code: label }), true, name);
    assert.equal(context.cricketHuntInfo(17), 0, name);
  }
  assert.equal(context.releaseCricketHuntKey({ key: "x", code: "KeyX" }), false, "X is not one of its keys");
  // D held for 0.5 s turns the head 45 degrees right.
  const before = context.cricketHuntInfo(15);
  key("d");
  for (let i = 0; i < 5; i++) tick(100);
  assert.ok(Math.abs(context.cricketHuntInfo(15) - before - 785) <= 1, String(context.cricketHuntInfo(15) - before));
  context.releaseCricketHuntKey({ key: "d", code: "KeyD" });
  // Space grabs at nothing, three times: the try is judged.
  for (let i = 0; i < 3; i++) key(" ");
  assert.equal(context.cricketHuntInfo(12), 3);
  tick(100);
  assert.equal(context.cricketHuntInfo(0), 2);
  assert.equal(context.cricketHuntInfo(8), 3);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("cricketHuntRun", context), 0n);
} finally {
  context.destroyCricketHuntRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Cricket Hunt web shell options, ten held keys, grabs, clock, and disposal passed");
