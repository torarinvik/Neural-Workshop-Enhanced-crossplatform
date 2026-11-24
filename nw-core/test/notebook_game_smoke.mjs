import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { decode, Kind } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { TASK_IDS_BY_CATEGORY } from "../shells/web/task-registry.js";

const { exports: api, instance, createNotebookEnvironment } = await instantiateElisa(
  fs.readFileSync(process.env.NWCORE_WASM_PATH ?? new URL("../build/nwcore.wasm", import.meta.url)),
  { warn: false },
);
const task = api.nw_api_v1_task_notebook();
assert.equal(task, 1307337504n);
assert.equal(api.nw_api_v1_supports(task, 1n), 1n);
const create = (rung, count) => api.nw_api_v1_create(task, 1n, rung, count, 1n, 0n, 0n, 0n, 17n);
assert.equal(create(2n, 1n), -3n);
assert.equal(create(1n, 2n), -3n);
assert.equal(api.nw_api_v1_create(task, 1n, 999999999999n, 1n, 1n, 1n, 0n, 0n, 17n), -3n);
assert.deepEqual(TASK_IDS_BY_CATEGORY[1], ["concentration", "recognition", "trivia", "notebook", "where_was_it"]);

const capacity = 131072n;
const buffer = api.nw_frame_alloc(capacity);
const bytes = size => new Uint8Array(instance.exports.memory.buffer, Number(buffer), Number(size));
const text = size => new TextDecoder().decode(bytes(size));
assert.equal(text(api.nw_notebook_options_note(buffer, capacity, 16n)),
  "Rung 16: 16 codes, up to 8 waiting at once, at least 8 cards before each is asked; 7 notebook lines." +
  "  With cards not needed, codes that change.  Some will have to be kept in your head.");
const hub = decode(bytes(api.nw_taskhub_write(buffer, capacity, 1n, 3n, 0n, 912n, 684n)));
assert.ok(hub.some(command => command.text === "Notebook"));

const run = create(1n, 1n);
assert.ok(run > 0n);
let sequence = 0n;
const key = (at, code, modifiers = 0n) =>
  api.nw_api_v1_dispatch(run, 2n, BigInt(at), sequence++, BigInt(code), 0n, modifiers, 0n, 0n, 0n, 0n);
const pointer = (at, x, y) =>
  api.nw_api_v1_dispatch(run, 5n, BigInt(at), sequence++, 0n, 0n, 0n, 0n,
    BigInt(Math.round(x * 1e6 / 912)), BigInt(Math.round(y * 1e6 / 684)), 0n);
const info = field => api.nw_api_v1_notebook_info(run, BigInt(field));
const texts = () => decode(bytes(api.nw_api_v1_render(run, buffer, capacity, 0n, 912n, 684n)))
  .filter(command => command.kind === Kind.TEXT).map(command => command.text);
assert.ok(texts().includes("Press Space or click to start"));
assert.equal(key(0, 1), 1n);
assert.equal(info(0), 1n);
assert.equal(info(6), 2n);
assert.equal(info(17), 0n);
const fact = texts().find(label => /^[A-Za-z]+ [A-Za-z]+: [1-9][0-9]{2}$/.test(label));
assert.ok(fact);
const [name, code] = fact.split(": ");
assert.equal(info(12), -1n);
assert.equal(key(1, 12), 2n);
assert.equal(key(1, 12, 1n), 1n);
assert.equal(key(1, 19, 1n), 2n);
assert.ok(texts().includes(name + " " + code));
assert.equal(pointer(2, 224, 325), 1n);
assert.equal(info(17), 3n);
assert.ok(texts().includes(name + "?"));
assert.ok(!texts().includes(fact));
assert.equal(key(2, 12, 1n), 2n);
assert.equal(key(2, 2), 2n);
const answer = [info(12), info(13)].indexOf(BigInt(code));
assert.ok(answer >= 0);
assert.equal(info(14), -1n);
assert.equal(info(18), 0n);
assert.equal(info(19), -6n);
assert.equal(api.nw_api_v1_read_state(run, buffer, capacity), 112n);
assert.equal(key(3, 12 + answer), 1n);
assert.equal(info(0), 2n);
assert.equal(info(1), 2n);
assert.equal(info(8), 1n);
assert.ok(texts().includes("1 of 1 answered right"));
assert.equal(info(12), -1n);
assert.equal(api.nw_api_v1_advance(run, 2502n, 0n, sequence++), 2n);
assert.equal(api.nw_api_v1_advance(run, 2503n, 0n, sequence++), 1n);
assert.equal(info(0), 3n);
assert.ok(texts().includes("1 of 1 passed   highest rung passed 1"));
assert.equal(api.nw_api_v1_destroy(run), 0n);
assert.equal(info(0), -1n);
const html = fs.readFileSync(new URL("../shells/web/index.html", import.meta.url), "utf8");
const hooks = html.slice(html.indexOf("const NOTEBOOK_SETTINGS"), html.indexOf("const WHERE_WAS_IT_SETTINGS"));
const keyHandler = html.slice(html.indexOf('    if (isNotebookTask()) {\n      if (!notebookOptionsForm.hidden)'),
  html.indexOf('    if (isWhereWasItTask()) {\n      if (!whereWasItOptionsForm.hidden)'));
const stored = new Map();
const listeners = new Map();
const note = {};
const form = {
  hidden: true,
  elements: {
    rung: { focus() {}, addEventListener: (event, callback) => listeners.set(event, callback) },
    rounds: {}, adaptive: {},
  },
  addEventListener: (event, callback) => listeners.set(event, callback),
  querySelector: () => ({ addEventListener: (event, callback) => listeners.set(event, callback) }),
};
let host;
host = vm.createContext({
  exports: api, framePtr: Number(buffer), FRAME_CAPACITY: Number(capacity), view: bytes, TextDecoder,
  canvas: { width: 912, height: 684, focus() {} }, screen: "taskhub",
  document: { getElementById: id => id === "notebook-options" ? form : note },
  localStorage: { getItem: key => stored.get(key), setItem: (key, value) => stored.set(key, value) },
  isTaskId: id => id === "notebook",
  apiCreateRun: (id, values, seed) => api.nw_api_v1_create(id, 1n, ...values, BigInt(seed)),
  apiDestroyRun: handle => api.nw_api_v1_destroy(handle),
  apiDispatchKey: (handle, code, event) =>
    api.nw_api_v1_dispatch(handle, 2n, 0n, sequence++, BigInt(code), 0n,
      event.shiftKey ? 1n : 0n, 0n, 0n, 0n, 0n),
  API_KEY: { space: 1, enter: 2, one: 12 },
  launchTask() { host.screen = "task"; },
  setScreen(screen) { host.screen = screen; },
  draw() {},
});
vm.runInContext(hooks + "\nfunction sendNotebookKey(event) {\n" + keyHandler + "\n}", host);
host.openNotebookOptions(true);
assert.equal(form.elements.rounds.value, 3);
form.elements.rung.value = 3;
form.elements.rounds.value = 1;
listeners.get("change")();
assert.match(note.textContent, /^Rung 3:/);
listeners.get("submit")({ preventDefault() {} });
assert.equal(host.screen, "taskhub");
host.launchTask();
assert.equal(host.notebookInfo(1), 3);
assert.equal(host.notebookInfo(3), 1);
host.sendNotebookKey({ key: " ", code: "Space", preventDefault() {} });
host.sendNotebookKey({ key: "!", code: "Digit1", shiftKey: true, preventDefault() {} });
const browserFrame = decode(host.notebookFrame(false)).map(command => command.text);
const browserFact = browserFrame.find(label => label?.match(/^[A-Za-z]+ [A-Za-z]+: [1-9][0-9]{2}$/));
assert.ok(browserFact && browserFrame.includes(browserFact.replace(": ", " ")));
host.destroyNotebookRun();
api.nw_frame_free(buffer);
console.log("PASS: Notebook hub, option preview, writing and answers, private state, verdict, and cleanup");

const canvas = { width: 912, height: 684 };
const pixels = new Uint8ClampedArray(canvas.width * canvas.height * 4);
const drawn = [];
const context = {
  canvas,
  save() {}, restore() {}, setTransform() {}, translate() {}, scale() {}, rotate() {},
  fillRect() {}, strokeRect() {}, beginPath() {}, arc() {}, fill() {}, stroke() {},
  moveTo() {}, lineTo() {}, closePath() {},
  clearRect() { pixels.fill(0); drawn.length = 0; },
  fillText(label) {
    drawn.push(label);
    const colors = {
      "rgba(64,255,64,1.000)": [64, 255, 64, 255],
      "rgba(255,64,64,1.000)": [255, 64, 64, 255],
    };
    const color = colors[this.fillStyle];
    if (color) {
      pixels.set(color, pixels.length - 4);
      pixels.set(color, pixels.length - 4 - canvas.width * 4);
    }
  },
  getImageData() { return { data: pixels }; },
};

const environment = createNotebookEnvironment(context, { seed: 17, trials: 1 });
assert.equal(environment.n_actions, 13);
const visibleFact = drawn.find(label => /^[A-Za-z]+ [A-Za-z]+: [1-9][0-9]{2}$/.test(label));
assert.ok(visibleFact);
const [visibleName, visibleCode] = visibleFact.split(": ");
assert.equal(environment.step(4)[0].outcome, undefined);
assert.ok(drawn.includes(visibleName + " " + visibleCode));
assert.equal(environment.step(12)[0].outcome, undefined);
assert.ok(drawn.includes(visibleName + "?"));
const answerLabel = drawn.find(label => /^[1-4]: [1-9][0-9]{2}$/.test(label) && label.endsWith(visibleCode));
const choice = Number(answerLabel?.[0]) - 1;
assert.ok(choice >= 0 && choice < 2);
const receipt = environment.act(choice);
assert.ok(receipt.ok);
assert.equal(environment.act(0).ok, false);
const verdict = environment.advance();
assert.equal(verdict.outcome.scalar, 1);
assert.equal(verdict.outcome.receipt_id, receipt.receipt_id);
assert.ok(environment.verify(verdict.outcome, verdict));
assert.equal(environment.step()[2], true);
assert.equal(environment.reset(17).frame_seq, 1);
environment.close();

const clock = createNotebookEnvironment(context, {
  seed: 17, rung: 2, trials: 2, frameHz: 20, thinkSeconds: 0.1, refillSeconds: 0.05,
});
assert.equal(clock.step()[0].outcome, undefined);
const flag = clock.step()[0];
assert.equal(flag.outcome.scalar, -1);
assert.ok(drawn.includes("Out of time"));
assert.ok(clock.verify(flag.outcome, flag));
assert.equal(clock.forfeits, 1);
assert.equal(clock.think_left, 0);
assert.equal(clock.step()[2], false);
assert.equal(clock.think_left, 0.05);
assert.equal(clock.step()[0].outcome.scalar, -1);
assert.equal(clock.step()[2], true);
clock.close();

const neutral = createNotebookEnvironment(context, { trials: 1, runtimePorts: 14, neutralOutcomes: true });
const quiet = neutral.step(13)[0];
assert.equal(quiet.outcome.scalar, 0);
assert.ok(neutral.verify(quiet.outcome, quiet));
neutral.close();
console.log("PASS: stepped Notebook public cards, receipts, verdict, think forfeits, refill, reset, and neutral ports");
