import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { attachPassageCaches } from "../shells/web/rung-env.js";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const artifact = fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url));
const instance = await instantiateElisa(artifact, { warn: false });
const { exports } = instance;
const listeners = new Map();
const settings = new Map();
const storage = new Map();
const framePtr = exports.nw_frame_alloc(1048576n);
const bind = id => ({
  addEventListener(type, handler) { listeners.set(`${id}:${type}`, handler); },
});
const options = {
  ...bind("form"),
  hidden: true,
  elements: { rung: { ...bind("rung"), focus() {} }, rounds: {}, adaptive: {} },
  querySelector: () => bind("cancel"),
};
const files = { ...bind("files"), files: [] };
const cacheStatus = {};
const note = {};
const elements = new Map([
  ["full-stop-options", options], ["full-stop-options-note", note],
  ["full-stop-cache-files", files], ["full-stop-cache-status", cacheStatus],
  ["full-stop-cache-clear", bind("clear")],
]);
const context = vm.createContext({
  exports, instance, attachPassageCaches, framePtr, FRAME_CAPACITY: 1048576, TextDecoder,
  document: { getElementById: id => elements.get(id) },
  window: {},
  canvas: { width: 912, height: 684, focus() {} },
  performance: { now: () => 0 },
  localStorage: { getItem: key => settings.get(key), setItem: (key, value) => settings.set(key, value) },
  crosswordIndexRequest: (_mode, operation) => Promise.resolve(operation({
    put: (value, key) => storage.set(key, value),
    delete: key => storage.delete(key),
  })),
  isTaskId: id => id === "full_stop",
  view: length => new Uint8Array(exports.memory.buffer, Number(framePtr), length),
  decisionsRunSeed: () => 17n,
  apiCreateRun: (task, args, seed) => exports.nw_api_v1_create(task, 1n, ...args, seed),
  apiDestroyRun: handle => exports.nw_api_v1_destroy(handle),
  launchTask() {}, draw() {},
});
const first = html.indexOf("const FULL_STOP_SETTINGS");
const last = html.indexOf("const MISSING_WORD_SETTINGS", first);
assert.ok(first >= 0 && last > first);
vm.runInContext(html.slice(first, last), context);
assert.match(html, /event\.key\.toLowerCase\(\) === "c" && isFullStopTask\(\)\) openFullStopOptions\(true\)/);

try {
  context.openFullStopOptions();
  assert.equal(options.hidden, false);
  assert.equal(options.elements.rounds.value, 5);
  assert.equal(note.textContent, "Rung 1: 2 sentences run together.");
  const oldHandle = context.ensureFullStopRun();
  files.files = [{
    name: "passages.txt",
    arrayBuffer: async () => new TextEncoder()
      .encode("Ada built a wooden boat. Clara painted it bright red.\n".repeat(100)).buffer,
  }];
  await listeners.get("files:change")();
  assert.equal(cacheStatus.textContent, "Using imported passages.");
  assert.ok(storage.has("full-stop-caches"));
  assert.equal(options.hidden, false);
  options.elements.rounds.value = "1";
  options.elements.adaptive.checked = false;
  listeners.get("form:submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get("nw.full_stop.options.v1")), { rung: 1, rounds: 1, adaptive: false });
  const handle = context.ensureFullStopRun();
  assert.notEqual(oldHandle, handle);
  assert.equal(exports.nw_api_v1_dispatch(handle, 2n, 0n, 0n, 1n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
  assert.ok(decode(context.fullStopFrame(true)).some(command => command.text === "Ada"));
  context.destroyFullStopRun();
  await listeners.get("clear:click")();
  assert.equal(cacheStatus.textContent, "Using bundled passages.");
  assert.equal(storage.has("full-stop-caches"), false);
} finally {
  context.destroyFullStopRun();
  exports.nw_frame_free(framePtr);
}
console.log("PASS: Full Stop browser option edits, imported passages, storage, and reset");
