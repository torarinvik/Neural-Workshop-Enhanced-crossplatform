import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const bytes = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const { exports } = await instantiateElisa(bytes, { warn: false });
const settings = new Map();
const timers = new Map();
const listeners = new Map();
let timerId = 0;
let now = 0;
let downloaded;
let filename;
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
  exports, TextDecoder, TextEncoder, URLSearchParams, Blob, location: { search: "?cipher_abyss-seed=17" },
  URL: { createObjectURL(blob) { downloaded = blob; return "blob:fixture"; }, revokeObjectURL() {} },
  document: {
    hidden: false,
    getElementById: id => id === "cipher-abyss-options" ? form : note,
    createElement: tag => {
      assert.equal(tag, "a");
      return { click() { filename = this.download; } };
    },
  },
  localStorage: { getItem: key => settings.get(key) ?? null, setItem: (key, value) => settings.set(key, value) },
  framePtr: exports.nw_frame_alloc(1048576n), FRAME_CAPACITY: 1048576,
  performance: { now: () => now },
  physicalKeyCode: () => 0,
  API_EVENT: { keyDown: 2n },
  requestAnimationFrame: callback => { timers.set(++timerId, callback); return timerId; },
  cancelAnimationFrame: id => timers.delete(id),
  setTimeout: callback => callback(),
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
  const isTaskId = id => id === "cipher_abyss";
  const view = length => new Uint8Array(exports.memory.buffer, Number(framePtr), length);
  const setScreen = next => { if (next === "taskhub") destroyCipherAbyssRun(); screen = next; };
  const launchTask = () => setScreen("task");
  ${extract("function apiNextSequence(", "function apiDispatchKeyUp(")}
  ${extract("function apiAdvance(", "function titleFrame(")}
  ${extract("function decisionsRunSeed(", "function ensureSonarRun(")}
  ${extract("const CIPHER_ABYSS_SETTINGS", "const controlsResizeObserver")}
`, context);

function tick(dt) {
  now += dt;
  assert.equal(timers.size, 1);
  const [id, callback] = timers.entries().next().value;
  timers.delete(id);
  callback();
}
try {
  assert.match(html, /isCipherAbyssTask\(\)\) openCipherAbyssOptions\(true\)/);
  assert.match(html, /if \(!event.repeat\) downloadCipherAbyssNotebook\(\)/);
  assert.match(extract("function setScreen(", "function draw("), /if \(isCipherAbyssTask\(\)\) destroyCipherAbyssRun\(\);/);
  context.openCipherAbyssOptions(true);
  assert.equal(form.hidden, false);
  assert.equal(form.elements.rounds.value, 5);
  assert.match(note.textContent, /Rung 1 \(patterns\)/);
  form.elements.rounds.value = "1";
  form.elements.adaptive.checked = false;
  listeners.get("submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.cipher_abyss.options.v1")), { rung: 1, rounds: 1, adaptive: false });
  assert.equal(vm.runInContext("screen", context), "taskhub");

  const libraryKey = "cipher_abyss_library.json";
  const prior = {version: 1, operators: {rev: 2, shift: 7}};
  settings.set(libraryKey, JSON.stringify(prior));
  vm.runInContext('launchTask(); cipherAbyssKey(CIPHER_ABYSS_KEYS.get(" "));', context);
  assert.equal(context.cipherAbyssInfo(0), 1);
  for (const code of [12, 13, 12, 2]) context.cipherAbyssKey(code);
  assert.equal(context.cipherAbyssInfo(11), 1);
  context.downloadCipherAbyssNotebook();
  assert.equal(filename, "cipher_abyss_notebook.txt");
  assert.match(await downloaded.text(), / 1  0 1 0 -> [01] [01] [01]/);
  for (let i = 0; i < 3301 && context.cipherAbyssInfo(0) === 1; i++) tick(100);
  assert.equal(context.cipherAbyssInfo(0), 2);
  assert.deepEqual(JSON.parse(settings.get(libraryKey)), prior);
  assert.equal(settings.get("cipher_abyss_tutorial_seen"), "1");
  assert.equal(JSON.parse(settings.get("cipher_abyss_rounds.jsonl")).experiments, 1);
  tick(9001);
  assert.equal(context.cipherAbyssInfo(0), 3);
  assert.equal(settings.get("cipher_abyss_rounds.jsonl").trim().split("\n").length, 1);
  vm.runInContext('setScreen("taskhub");', context);
  vm.runInContext('launchTask(); cipherAbyssKey(CIPHER_ABYSS_KEYS.get(" "));', context);
  for (const code of [89, 12, 12, 13, 2, 12, 12, 12, 2]) context.cipherAbyssKey(code);
  tick(100);
  assert.equal(context.cipherAbyssInfo(0), 2);
  assert.deepEqual(JSON.parse(settings.get(libraryKey)), {
    version: 1, operators: {rev: 2, rot: 1, shift: 1},
  });
  vm.runInContext('setScreen("taskhub");', context);
  assert.equal(timers.size, 0);
  assert.equal(vm.runInContext("cipherAbyssRun", context), 0n);
} finally {
  context.destroyCipherAbyssRun();
  exports.nw_frame_free(context.framePtr);
}
console.log("Cipher Abyss browser shell options, notebook download, tutorial, metrics, and operator storage, and disposal passed");
