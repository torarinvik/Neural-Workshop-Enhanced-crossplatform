import assert from "node:assert/strict";
import fs from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import vm from "node:vm";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

const wasm = process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url);
const { exports, instance, createCookieThiefEnvironment } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const task = exports.nw_api_v1_task_cookie_thief();
assert.equal(task, 2851280360n);
assert.equal(exports.nw_api_v1_supports(task), 1n);
assert.equal(exports.nw_api_v1_create(task, 1n, 1n, 1n, 0n, 0n, 0n, 0n, 42n), -3n);
const framePtr = Number(exports.nw_frame_alloc(65536n));
const statePtr = Number(exports.nw_frame_alloc(112n));

function info(handle, field) {
  return Number(exports.nw_api_v1_cookie_thief_info(handle, BigInt(field)));
}
function render(handle) {
  const length = Number(exports.nw_api_v1_render(handle, BigInt(framePtr), 65536n, 0n, 912n, 684n));
  assert.ok(length > 16);
  return decode(new Uint8Array(instance.exports.memory.buffer, framePtr, length));
}
const handle = exports.nw_api_v1_create(task, 1n, 1n, 1n, 80n, 250n, 0n, 0n, 42n);
assert.ok(handle > 0n);
let sequence = 0n;
const key = (time, code) => exports.nw_api_v1_dispatch(
  handle, 2n, BigInt(time), sequence++, BigInt(code), 0n, 0n, 0n, 0n, 0n, 0n);
const advance = (time) => exports.nw_api_v1_advance(handle, BigInt(time), 0n, sequence++);
assert.equal(key(0, 1), 1n);
assert.equal(advance(249), 2n);
assert.equal(key(249, 4), 2n); // Grabs are ignored during setup.
assert.equal(advance(250), 1n);
assert.equal(key(250, 4), 1n);
assert.equal(key(250, 6), 1n);
assert.equal(advance(250), 1n);
assert.equal(info(handle, 0), 3);
assert.equal(info(handle, 12), 1);
assert.equal(key(1249, 1), 2n); // The verdict has a one-second hold.
assert.equal(key(1250, 1), 1n);
assert.equal(exports.nw_api_v1_read_state(handle, BigInt(statePtr), 112n), 112n);
const view = new DataView(instance.exports.memory.buffer, statePtr, 112);
assert.deepEqual(Array.from({ length: 12 }, (_, i) => Number(view.getBigInt64(16 + i * 8, true))),
  [4, 1, 1, 1, 80, 250, 0, 1, 1, 0, 1, 1]);
const summary = render(handle).map(({ text }) => text);
assert.ok(summary.some((text) => text?.startsWith("1 of 1 clean, 1 points off 1 cookies")));
assert.ok(summary.includes("Away with 1 — +1 points"));
assert.equal(exports.nw_api_v1_destroy(handle), 0n);
assert.equal(info(handle, 0), -1);

// Rung ten with seed 42 has a safe golden reach and later a seen grab.
for (const enabled of [0n, 1n]) {
  const coached = exports.nw_api_v1_create(task, 1n, 10n, 1n, 125n, 250n, 0n, enabled, 42n);
  assert.ok(coached > 0n);
  assert.equal(info(coached, 14), Number(enabled));
  const act = (time, code) => exports.nw_api_v1_dispatch(
    coached, 1n, BigInt(time), sequence++, BigInt(code), 0n, 0n, 0n, 0n, 0n, 0n);
  assert.equal(act(0, 0), 1n);
  for (let tick = 0; tick <= 45; tick++) {
    const ms = tick * 125;
    if (info(coached, 0) === 2) {
      const action = tick % 3 === 0 ? 4 : tick % 3 === 1 ? 3 : 1;
      act(ms, action);
    }
    exports.nw_api_v1_advance(coached, BigInt(ms), 0n, sequence++);
    if (![38, 39, 44, 45].includes(tick)) continue;
    const expected = tick === 38 ? 1 : tick === 44 ? 0 : -1;
    assert.equal(info(coached, 10), -1, "round verdict remains separate from coaching");
    assert.equal(info(coached, 15), enabled ? expected : -1);
    const label = render(coached).find(({ kind, text }) =>
      kind === Kind.TEXT && (text === "Got one" || text === "She saw that"));
    if (enabled && expected >= 0) {
      assert.equal(label?.text, expected === 1 ? "Got one" : "She saw that");
      assert.equal(label?.color, expected === 1 ? 0x40ff40ff : 0xff4040ff);
    } else {
      assert.equal(label, undefined);
    }
  }
  assert.equal(exports.nw_api_v1_destroy(coached), 0n);
}

// Drive the production browser hooks with a virtual clock and animation
// callbacks. This exercises event routing and cleanup without a browser.
const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
assert.match(html, /cookieThief: exports\.nw_api_v1_task_cookie_thief\(\)/);
assert.match(html, /if \(isCookieThiefTask\(\)\) \{\s*destroyCookieRun\(\);\s*ensureCookieRun\(\);/);
assert.match(html, /if \(isCookieThiefTask\(\)\) destroyCookieRun\(\);/);
assert.match(html, /else if \(isCookieThiefTask\(\)\) \{\s*bytes = cookieFrame\(dark\(\)\)/);
const hooks = html.slice(html.indexOf("const COOKIE_PHASE"), html.indexOf("function isMazeTask"));
const keys = html.slice(html.indexOf('    if (isCookieThiefTask()) {\n      const key = event.key'),
  html.indexOf('    if (isMazeTask()) {\n      if ([" ", "Enter", "Escape", "c", "C", "r", "R"'));
let now = 0n;
let nextFrame = 0;
const pending = new Map();
const saved = new Map();
const host = vm.createContext({
  screen: "task", framePtr, FRAME_CAPACITY: 65536, canvas: { width: 912, height: 684 },
  exports, API_TASK: { cookieThief: task }, cookieRunHandle: 0n, cookieFrameHandle: null,
  isTaskId: (id) => id === "cookie_thief", draw: () => {},
  localStorage: { getItem: (key) => saved.get(key), setItem: (key, value) => saved.set(key, value) },
  referencePointFromEvent: (event) => event,
  apiCreateRun: (id, options, seed) => exports.nw_api_v1_create(id, 1n, ...options, seed),
  apiDispatchAction: (id, action) => exports.nw_api_v1_dispatch(
    id, 1n, now, sequence++, BigInt(action), 0n, 0n, 0n, 0n, 0n, 0n),
  apiAdvance: (id) => exports.nw_api_v1_advance(id, now, 0n, sequence++),
  apiDestroyRun: (id) => exports.nw_api_v1_destroy(id),
  requestAnimationFrame: (callback) => { pending.set(++nextFrame, callback); return nextFrame; },
  cancelAnimationFrame: (id) => pending.delete(id),
  view: (length) => new Uint8Array(instance.exports.memory.buffer, framePtr, length),
});
host.setScreen = (screen) => {
  if (host.screen === "task" && screen === "taskhub") host.destroyCookieRun();
  if (host.screen === "cookieOptions" && screen !== "cookieOptions")
    vm.runInContext("cookieOptionsDraft = null; cookieOptionsReturn = null;", host);
  host.screen = screen;
};
vm.runInContext(hooks + "\nfunction sendKey(event) {\n" + keys + "\n}", host);
const send = (input) => {
  let prevented = false;
  host.sendKey({ key: input, preventDefault() { prevented = true; } });
  assert.ok(prevented);
};
const tick = (time) => {
  now = BigInt(time);
  assert.equal(pending.size, 1);
  const [[id, callback]] = pending;
  pending.delete(id);
  callback();
};
const browserRun = host.ensureCookieRun();
assert.equal(info(browserRun, 1), 4);
assert.equal(info(browserRun, 3), 5);
assert.ok(decode(host.cookieFrame(false)).some(({ text }) => text === "Cookie Thief"));
send("c");
assert.equal(host.screen, "cookieOptions");
host.cookieOptionsKey({ key: "ArrowLeft", preventDefault() {} });
const preview = decode(host.cookieOptionsFrame(false)).map(({ text }) => text);
assert.ok(preview.includes("Cookie Thief options"));
assert.ok(preview.some((text) => text?.startsWith("Take 7 and leave")));
assert.ok(preview.some((text) => text?.includes("Guessing gets away clean")));
host.cookieOptionsKey({ key: "Escape", preventDefault() {} });
assert.equal(host.screen, "task");
assert.equal(info(browserRun, 1), 4);
assert.equal(saved.size, 0);
send(" ");
tick(799);
assert.equal(info(browserRun, 0), 1);
tick(800);
assert.equal(info(browserRun, 0), 2);
send("c");
assert.equal(host.screen, "task");
send("X");
send("ArrowDown");
tick(800);
assert.equal(info(browserRun, 0), 3);
assert.equal(pending.size, 0);
assert.ok(decode(host.cookieFrame(false)).some(({ text }) => text === "Only 1 of 9 — +1 points"));
now = 1800n;
send("Enter");
assert.equal(info(browserRun, 2), 2);
assert.equal(pending.size, 1);
send("Escape");
assert.equal(host.screen, "taskhub");
assert.equal(info(browserRun, 0), -1);
assert.equal(pending.size, 0);
host.openCookieOptions("taskhub");
host.cookieOptionsKey({ key: "ArrowRight", preventDefault() {} });
host.cookieOptionClick({ x: 456, y: 378 }); // Select beat duration.
host.cookieOptionClick({ x: 456, y: 378 }); // 160 ms -> 250 ms.
host.cookieOptionsKey({ key: "PageDown", preventDefault() {} });
host.cookieOptionsKey({ key: " ", preventDefault() {} });
host.cookieOptionsKey({ key: "Enter", preventDefault() {} });
assert.equal(host.screen, "taskhub");
const storageKey = "nw-cookie-thief-options";
assert.deepEqual(JSON.parse(saved.get(storageKey)), [5, 5, 250, 800, 0]);
vm.runInContext("cookieOptions = readCookieOptions();", host);
const nextRun = host.ensureCookieRun();
assert.equal(info(nextRun, 1), 5);
assert.equal(info(nextRun, 4), 250);
assert.equal(info(nextRun, 6), 0);
host.screen = "task";
send("c");
host.cookieOptionsKey({ key: "ArrowLeft", preventDefault() {} });
host.cookieOptionsKey({ key: "Enter", preventDefault() {} });
assert.equal(host.screen, "task");
assert.equal(host.ensureCookieRun(), nextRun, "applying settings preserves the live RNG stream");
assert.equal(info(nextRun, 1), 4);
host.destroyCookieRun();
saved.set(storageKey, "[4,5,13,800,1]");
vm.runInContext("cookieOptions = readCookieOptions();", host);
const fallback = host.ensureCookieRun();
assert.equal(info(fallback, 4), 160);
host.destroyCookieRun();
console.log("PASS: Cookie Thief web lifecycle, keyboard routes, clock, verdict, coaching, options, and cleanup");

// Paint verdict commands into synthetic RGBA so the production stepped
// boundary can be replayed without relying on a window or system fonts.
const canvas = { width: 912, height: 684 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  fillRect() {}, strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {},
  moveTo() {}, lineTo() {}, closePath() {},
  clearRect() { pixels.fill(0); },
  fillText() {
    const labelColors = {
      "rgba(64,255,64,1.000)": [64, 255, 64, 255],
      "rgba(255,64,64,1.000)": [255, 64, 64, 255],
    };
    const color = labelColors[this.fillStyle];
    if (color) {
      pixels.set(color, pixels.length - 4);
      pixels.set(color, pixels.length - 4 - canvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};
const options = { seed: 42, rung: 1, trials: 1, beatMs: 1, setMs: 1, adaptive: false };
assert.throws(() => createCookieThiefEnvironment(context, { ...options, frameHz: 9 }), /10 frames/);
assert.throws(() => createCookieThiefEnvironment(context, { ...options, runtimePorts: 3 }), /four runtime ports/);
const stepped = createCookieThiefEnvironment(context, { ...options, runtimePorts: 0 });
assert.equal(stepped.n_actions, 4);
assert.equal(stepped.act(0).ok, false, "no action during setup");
const stimulus = stepped.advance();
const grab = stepped.act(0, -0.25);
assert.equal(grab.frame_seq, stimulus.frame_seq);
assert.deepEqual(Object.keys(stimulus).sort(),
  ["done", "frame_seq", "height", "rgba", "timestamp_ns", "width"]);
assert.match(grab.stimulus_digest, /^[0-9a-f]{64}$/);
assert.equal(grab.logp, -0.25);
assert.equal(stepped.act(1).ok, false, "one action per response window");
assert.equal(stepped.advance().outcome, undefined);
assert.equal(stepped.act([0, 1]).ok, false);
assert.equal(stepped.act({ leave: true }).ok, false);
const leave = stepped.act({ 1: true });
const [verdict, verdictEvents, verdictDone] = stepped.step();
assert.equal(verdictDone, false);
assert.deepEqual(verdictEvents, [{ type: "outcome", ...verdict.outcome }]);
assert.equal(verdict.outcome.receipt_id, leave.receipt_id);
assert.equal(verdict.outcome.scalar, 1);
assert.equal(verdict.outcome.evidence_digests.length, 3);
assert.equal(verdict.outcome.evidence_digests[0], grab.stimulus_digest);
assert.equal(stepped.verify(verdict.outcome, verdict), true);
assert.equal(stepped.act(0).ok, false, "no action on the verdict");
const [done, endEvents, runDone] = stepped.step();
assert.equal(done.outcome, undefined);
assert.equal(runDone, true);
assert.deepEqual(endEvents, [{ type: "run_end", frame_seq: done.frame_seq, timestamp_ns: done.timestamp_ns }]);
const [held, repeatedEvents] = stepped.step();
assert.equal(held.frame_seq, done.frame_seq);
assert.deepEqual(repeatedEvents, []);
const stats = stepped.accounting.snapshot();
assert.equal(stats.logical_trials, 1);
assert.equal(stats.significant_frames, 5);
assert.equal(stats.unique_public_outcome_bits, 1);
assert.equal(stats.dropped_frames, 0);
assert.equal(stats.duplicate_frames, 0);
assert.equal(stats.action_to_outcome_latency_ms.length, 1);
assert.ok(stats.action_to_outcome_latency_ms[0] >= 0);
assert.equal(stepped.reset(42).frame_seq, 1);
assert.equal(stepped.getReceipt(leave.receipt_id), undefined);
assert.equal(stepped.accounting.snapshot().unique_public_outcome_bits, 0);
const fresh = stepped.observe();
fresh.rgba[0] = 255;
assert.equal(stepped.observe().rgba[0], 0);
stepped.close();
stepped.close();
assert.equal(stepped.getReceipt(leave.receipt_id), undefined);
assert.throws(() => stepped.advance(), /closed/);

const idle = createCookieThiefEnvironment(context, options);
idle.advance();
let idleVerdict;
for (let tick = 0; tick < 100 && !idleVerdict; tick++) {
  const candidate = idle.advance();
  if (candidate.outcome) idleVerdict = candidate;
}
assert.equal(idleVerdict.outcome.scalar, -1);
assert.equal(idle.verify(idleVerdict.outcome, idleVerdict), true);
idle.close();

const dense = createCookieThiefEnvironment(context, { ...options, neutralOutcomes: true, runtimePorts: 8 });
assert.equal(dense.n_actions, 8);
dense.advance();
const wait = dense.act(3);
const quiet = dense.advance();
assert.equal(wait.ok, true);
assert.equal(quiet.outcome.receipt_id, wait.receipt_id);
assert.equal(quiet.outcome.scalar, 0);
assert.equal(dense.verify(quiet.outcome, quiet), true);
const altered = structuredClone(quiet);
altered.rgba[0] ^= 1;
assert.equal(dense.verify(quiet.outcome, altered), false);
assert.equal(dense.verify({ ...quiet.outcome, scalar: 1 }, quiet), false);
assert.equal(dense.verify({ ...quiet.outcome, receipt_id: wait.receipt_id + 1 }, quiet), false);
const extra = dense.act([7]);
assert.equal(extra.ok, true);
assert.equal(dense.advance().outcome.receipt_id, extra.receipt_id);
dense.close();
console.log("PASS: stepped Cookie Thief observations, receipts, events, accounting, reset, and cleanup");

assert.throws(() => createCookieThiefEnvironment(context, { ...options, thinkSeconds: 1 }), /already clocked/);
assert.throws(() => createCookieThiefEnvironment(context, { ...options, frameExport: new ArrayBuffer(36) }),
  /SharedArrayBuffer/);
assert.throws(() => createCookieThiefEnvironment(context, { ...options, frameExport: new SharedArrayBuffer(36) }),
  /too small/);
const shared = new SharedArrayBuffer(36 + pixels.length);
const exporting = createCookieThiefEnvironment(context, { ...options, frameExport: shared });
assert.equal(exporting.think_left, 0);
assert.equal(exporting.forfeits, 0);
const pythonExport = fileURLToPath(new URL("../../original-neural-workshop-enhanced/nwenv/export.py", import.meta.url));
function pythonFrameHeader(sequence, timestamp, width, height, consumed = false) {
  const result = spawnSync("python3", ["-c", `
import runpy
import sys
api = runpy.run_path(sys.argv[1])
sys.stdout.buffer.write(api["HEADER"].pack(api["MAGIC"], api["VERSION"], *map(int, sys.argv[2:])))
`, pythonExport, String(sequence), String(timestamp), String(width), String(height), consumed ? "1" : "0"]);
  assert.equal(result.status, 0, result.stderr.toString());
  return result.stdout;
}
function assertPublished(frame) {
  const serialized = Buffer.from(shared);
  assert.deepEqual(serialized.subarray(0, 36),
    pythonFrameHeader(frame.frame_seq, frame.timestamp_ns, frame.width, frame.height));
  assert.deepEqual(serialized.subarray(36), Buffer.from(frame.rgba));
}
assertPublished(exporting.observe());
assertPublished(exporting.advance());
exporting.act(0);
exporting.advance();
assertPublished(exporting.step(1)[0]);
assertPublished(exporting.advance());
assertPublished(exporting.reset(42));
canvas.width++;
assert.throws(() => exporting.advance(), /too small/);
canvas.width--;
assert.equal(exporting.advance().frame_seq, 2);
exporting.close();

const headerPtr = exports.nw_frame_alloc(36n);
try {
  const seq = 0xFEDCBA9876543210n;
  const stamp = 0x1234567890ABCDEFn;
  assert.equal(exports.nw_frame_export_header(headerPtr, 35n, seq, stamp, 912, 684, true), -1n);
  assert.equal(exports.nw_frame_export_header(0n, 36n, seq, stamp, 912, 684, true), -1n);
  assert.equal(exports.nw_frame_export_header(headerPtr, 36n, seq, stamp, 912, 684, true), 36n);
  const directHeader = Buffer.from(instance.exports.memory.buffer, Number(headerPtr), 36);
  assert.deepEqual(directHeader, pythonFrameHeader(seq, stamp, 912, 684, true));
} finally {
  exports.nw_frame_free(headerPtr);
}
console.log("PASS: Cookie Thief shared frame bytes match Python NWFB headers and preserve publish order");
