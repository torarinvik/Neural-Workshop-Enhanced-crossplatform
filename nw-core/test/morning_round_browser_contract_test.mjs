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
  document: { getElementById: id => id === "morning-round-options" ? form : note },
  exports, TextDecoder, URLSearchParams, location: { search: "?morning_round-seed=17" },
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
  const isTaskId = id => id === "morning_round";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyMorningRoundRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchText(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${extract("const MORNING_ROUND_SETTINGS", "const HEAVIER_SETTINGS")}
`, context);

try {
  assert.match(html, /event\.key\.toLowerCase\(\) === "c" && isMorningRoundTask\(\)\) openMorningRoundOptions\(true\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isMorningRoundTask\(\)\) destroyMorningRoundRun\(\);/);
  assert.match(html, /apiDispatchPointer\(handle, API_EVENT\.pointerDown, event\)/);
  context.openMorningRoundOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.match(note.textContent, /Rung 1: 1 rule\(s\), 1 block\(s\), 2 mistake\(s\) allowed\./);

  form.elements.rung.value = "16";
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  context.updateMorningRoundOptionsNote();
  assert.match(note.textContent, /Rung 16: 4 rule\(s\), 5 block\(s\)/);
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(form.hidden, true);
  assert.equal(vm.runInContext("screen", context), "taskhub");
  assert.deepEqual(JSON.parse(settings.get("nw.morning_round.options.v1")), { rung: 16, rounds: 1, adaptive: false });

  context.openMorningRoundOptions(true);
  assert.equal(form.elements.rung.value, 16);
  form.elements.rung.value = "25";
  listeners.get("click")();
  assert.equal(JSON.parse(settings.get("nw.morning_round.options.v1")).rung, 16);

  context.openMorningRoundOptions(true);
  form.elements.rung.value = "1";
  listeners.get("submit")({ preventDefault() {} });
  vm.runInContext('launchTask(); morningRoundKey(MORNING_ROUND_KEYS.get(" "));', context);
  assert.equal(context.morningRoundInfo(0), 1);
  assert.equal(timers.size, 1);
  const frame = elapsed => {
    now += elapsed;
    const [id, callback] = timers.entries().next().value;
    timers.delete(id);
    callback();
  };
  for (let i = 0; i < 25; i++) frame(100);
  const papers = context.morningRoundInfo(13);
  context.morningRoundKey(81);
  assert.equal(context.morningRoundInfo(13), papers - 1);
  context.morningRoundKey(3);
  context.morningRoundKey(79);
  assert.equal(context.releaseMorningRoundKey({ key: "ArrowLeft", code: "ArrowLeft", preventDefault() {} }), true);
  const x = context.morningRoundInfo(11);
  frame(100);
  assert.ok(context.morningRoundInfo(11) < x);
  context.clearMorningRoundControls(9n);
  const afterBlur = context.morningRoundInfo(11);
  frame(100);
  assert.equal(context.morningRoundInfo(11), afterBlur);
  for (let tick = 0; tick < 600 && context.morningRoundInfo(0) === 1; tick++) frame(100);
  assert.equal(context.morningRoundInfo(0), 2);
  assert.ok(audibleChunks > 0);
  assert.equal(timers.size, 1);
  frame(3500);
  assert.equal(context.morningRoundInfo(0), 3);
  const handle = vm.runInContext("morningRoundRun", context);
  context.openMorningRoundOptions();
  form.elements.rung.value = "4";
  listeners.get("submit")({ preventDefault() {} });
  assert.equal(vm.runInContext("morningRoundRun", context), handle);
  assert.equal(context.morningRoundInfo(0), 0);
  assert.equal(context.morningRoundInfo(8), 0);
  assert.equal(context.morningRoundInfo(6), 4);
  context.morningRoundKey(1);
  assert.equal(timers.size, 1);
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("morningRoundRun", context), 0n);
} finally {
  context.destroyMorningRoundRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Morning Round browser shell: options, persistence, held keys, focus cleanup, feedback, and disposal pass");
