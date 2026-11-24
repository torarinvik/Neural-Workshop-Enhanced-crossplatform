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
let audibleChunks = 0;
let pendingSamples;
class AudioContext {
  state = "running";
  destination = {};
  get currentTime() { return now / 1000; }
  createBuffer(channels, frames, rate) {
    assert.equal(channels, 2);
    assert.equal(rate, 22050);
    assert.ok(frames > 0 && frames <= 2205);
    pendingSamples = Array.from({ length: channels }, () => new Float32Array(frames));
    return { duration: frames / rate, getChannelData: index => pendingSamples[index] };
  }
  createBufferSource() {
    return {
      connect() {}, disconnect() {}, stop() { this.onended?.(); },
      start() {
        if (pendingSamples.some(channel => channel.some(sample => sample !== 0))) audibleChunks++;
      },
    };
  }
}
const context = vm.createContext({
  window: { AudioContext },
  document: { getElementById: id => id === "heavier-options" ? form : note },
  exports, TextDecoder, URLSearchParams, location: { search: "?heavier-seed=17" },
  localStorage: { getItem: key => settings.get(key), setItem: (key, value) => settings.set(key, value) },
  framePtr: exports.nw_frame_alloc(1048576n), FRAME_CAPACITY: 1048576,
  performance: { now: () => now },
  physicalKeyCode: () => 0,
  API_EVENT: { keyDown: 2n, keyUp: 3n, focus: 9n },
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
  const isTaskId = id => id === "heavier";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyHeavierRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchText(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${extract("const HEAVIER_SETTINGS", "const FULL_STOP_SETTINGS")}
`, context);

try {
  assert.match(html, /event\.key\.toLowerCase\(\) === "c" && isHeavierTask\(\)\) openHeavierOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isHeavierTask\(\)\) destroyHeavierRun\(\);/);
  assert.match(html, /apiDispatchPointer\(heavierRun, API_EVENT\.pointerMove, event, true, event.buttons\)/);
  assert.match(html, /apiDispatchPointer\(heavierRun, API_EVENT\.pointerUp, event, true\)/);
  context.openHeavierOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.match(note.textContent, /Rung 1: 3 crates, 5 boards\./);

  form.elements.rung.value = "16";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateHeavierOptionsNote();
  assert.match(note.textContent, /Rung 16: 4 crates, 4 boards\./);
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(form.hidden, true);
  assert.equal(vm.runInContext("screen", context), "taskhub");
  assert.deepEqual(JSON.parse(settings.get("nw.heavier.options.v1")), { rung: 16, rounds: 1, adaptive: false });

  context.openHeavierOptions(true);
  assert.equal(form.elements.rung.value, 16);
  form.elements.rung.value = "25";
  listeners.get("click")();
  assert.equal(JSON.parse(settings.get("nw.heavier.options.v1")).rung, 16);

  context.openHeavierOptions(true);
  form.elements.rung.value = "1";
  listeners.get("submit")({ preventDefault() {} });
  vm.runInContext('launchTask(); heavierKey(HEAVIER_KEYS.get(" "));', context);
  assert.equal(context.heavierInfo(0), 1);
  assert.equal(timers.size, 1);
  const frame = elapsed => {
    now += elapsed;
    const [id, callback] = timers.entries().next().value;
    timers.delete(id);
    callback();
  };
  context.heavierKey(12);
  assert.equal(context.heavierInfo(13), 0);
  frame(100);
  assert.ok(context.heavierInfo(14) > 0);
  assert.equal(context.releaseHeavierKey({ key: "1", code: "Digit1", preventDefault() {} }), true);
  assert.equal(context.heavierInfo(13), -1);
  context.heavierKey(13);
  assert.equal(context.heavierInfo(13), 1);
  context.clearHeavierControls(9n);
  assert.equal(context.heavierInfo(13), -1);
  context.heavierKey(85); // Choose crate 3 with C while playing.
  frame(100);
  assert.equal(context.heavierInfo(0), 2);
  for (let i = 0; i < 5; i++) frame(100);
  assert.ok(audibleChunks > 0);
  assert.equal(timers.size, 1);
  frame(2000);
  assert.equal(context.heavierInfo(0), 3);
  const handle = vm.runInContext("heavierRun", context);
  context.openHeavierOptions();
  form.elements.rung.value = "4";
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(vm.runInContext("heavierRun", context), handle);
  assert.equal(context.heavierInfo(0), 0);
  assert.equal(context.heavierInfo(8), 0);
  assert.equal(context.heavierInfo(6), 4);
  context.heavierKey(1);
  assert.equal(timers.size, 1);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("heavierRun", context), 0n);
} finally {
  context.destroyHeavierRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Heavier browser shell: options, persistence, held keys, focus cleanup, feedback, and disposal pass");
