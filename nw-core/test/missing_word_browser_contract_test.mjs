import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { attachPassageCaches } from "../shells/web/rung-env.js";
import { decode } from "../shells/web/display-list.js";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const proofreader = process.argv.includes("--proofreader");
const lines = process.argv.includes("--lines");
const argue = process.argv.includes("--argue");
const sense = process.argv.includes("--sense");
// Which Feeling reads goemotions.tsv instead.
const feel = process.argv.includes("--feel");
// How Strongly reads eqbench.jsonl, Reading People emobench.jsonl.
const strong = process.argv.includes("--strong");
const read = process.argv.includes("--read");
// Second Thoughts, Why They Feel, Tone of Voice and Emotion make their own questions: no import controls.
const why = process.argv.includes("--why");
const tone = process.argv.includes("--tone");
const emo = process.argv.includes("--emo");
const second = process.argv.includes("--second") || why || tone || emo;
// Figures of Speech, Between the Lines, Bad Argument and Social Sense read questions.jsonl.
const figures = process.argv.includes("--figures") || lines || argue || sense || feel || strong || read;
const task = emo ? "emotion" : tone ? "tone_of_voice" : why ? "why_they_feel" : second ? "second_thoughts" : read ? "reading_people" : strong ? "how_strongly" : feel ? "which_feeling" : sense ? "social_sense" : argue ? "bad_argument" : lines ? "between_the_lines" : figures ? "figures_of_speech" : proofreader ? "proofreader" : "missing_word";
let activeTask = task;
const title = emo ? "Emotion" : tone ? "Tone of Voice" : why ? "Why They Feel" : second ? "Second Thoughts" : read ? "Reading People" : strong ? "How Strongly" : feel ? "Which Feeling" : sense ? "Social Sense" : argue ? "Bad Argument" : lines ? "Between the Lines" : figures ? "Figures of Speech" : proofreader ? "The Proofreader" : "The Missing Word";
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
  setAttribute(key, value) { this[key] = value; },
  elements: { rung: { ...bind("rung"), focus() {} }, rounds: {}, adaptive: {} },
  querySelector: () => bind("cancel"),
};
const files = { ...bind("files"), files: [] };
const cacheStatus = {};
const note = {};
const cacheKey = read ? "emotion-story-cache" : strong ? "emotion-dialogue-cache" : feel ? "emotion-comment-cache" : figures ? "figures-question-cache" : "missing-word-caches";
const cacheUnit = read ? "stories" : strong ? "dialogues" : feel ? "comments" : figures ? "questions" : "passages";
const elements = new Map([
  ["missing-word-options", options], ["missing-word-options-note", note],
  ["missing-word-cache-files", files], ["missing-word-cache-status", cacheStatus],
  ["missing-word-cache-clear", bind("clear")],
  ["reading-rounds-label", {}], ["reading-import-label", {}], ["reading-import", {}],
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
  isTaskId: id => id === activeTask,
  view: length => new Uint8Array(exports.memory.buffer, Number(framePtr), length),
  decisionsRunSeed: () => 17n,
  apiCreateRun: (task, args, seed) => exports.nw_api_v1_create(task, 1n, ...args, seed),
  apiDestroyRun: handle => exports.nw_api_v1_destroy(handle),
  launchTask() {}, draw() {},
});
const first = html.indexOf("const MISSING_WORD_SETTINGS");
const last = html.indexOf("const DISPATCH_SETTINGS", first);
assert.ok(first >= 0 && last > first);
vm.runInContext(html.slice(first, last), context);
assert.match(html, /event\.key\.toLowerCase\(\) === "c" && isMissingWordTask\(\)\) openMissingWordOptions\(true\)/);

if (second) {
  try {
    context.openMissingWordOptions();
    assert.equal(options.hidden, false);
    assert.equal(options["aria-label"], `${title} options`);
    assert.equal(elements.get("reading-import").hidden, true);
    assert.equal(elements.get("reading-rounds-label").textContent, "Rounds per run");
    assert.equal(note.textContent, emo ? "Rung 1: 2 emotions to tell apart." : tone ? "Rung 1: 2 emotions to choose from." : why ? "Rung 1: 2 answers to choose from." : "Rung 1: race, pond, coin, counts.");
    context.ensureMissingWordRun();
    assert.equal(context.missingWordInfo(6), 1);
    options.elements.rung.value = "4";
    options.elements.rounds.value = "1";
    options.elements.adaptive.checked = false;
    listeners.get("form:submit")({ preventDefault() {} });
    assert.deepEqual(JSON.parse(settings.get(`nw.${task}.options.v1`)), { rung: 4, rounds: 1, adaptive: false });
    // The run is made again with the new settings (handles are reused, so
    // its settings tell, not its number).
    const handle = context.ensureMissingWordRun();
    assert.equal(context.missingWordInfo(3), 1);
    assert.equal(context.missingWordInfo(6), 4);
    assert.equal(context.missingWordInfo(7), 0);
    assert.equal(exports.nw_api_v1_dispatch(handle, 2n, 0n, 0n, 1n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
    const frame = decode(context.missingWordFrame(true));
    assert.ok(frame.some(command => command.text === title));
    assert.equal(storage.size, 0);
  } finally {
    context.destroyMissingWordRun();
    exports.nw_frame_free(framePtr);
  }
  console.log(`PASS: ${title} browser options without imports, settings, start and frame`);
  process.exit(0);
}

try {
  context.openMissingWordOptions();
  assert.equal(options.hidden, false);
  assert.equal(options["aria-label"], `${title} options`);
  assert.equal(elements.get("reading-rounds-label").textContent, figures ? "Rounds per run" : "Passages per run");
  assert.equal(files.multiple, !figures);
  assert.equal(options.elements.rounds.value, 5);
  assert.equal(elements.get("reading-import-label").textContent,
    read ? "Import emobench.jsonl" : strong ? "Import eqbench.jsonl" : feel ? "Import goemotions.tsv" : figures ? "Import questions.jsonl" : "Import passage caches");
  assert.equal(note.textContent, read ? "Rung 1: feel." : strong ? "Rung 1: which emotion is strongest." : feel ? "Rung 1: 2 answers to choose from." : sense ? "Rung 1: feel, describe." : argue ? "Rung 1: nonsense." : lines ? "Rung 1: implicature; 20 items." : figures ? "Rung 1: metaphor." :
    "Rung 1: 1 sentence(s), 1 mistake(s) to mend.");
  const oldHandle = context.ensureMissingWordRun();
  files.files = [{
    name: read ? "emobench.jsonl" : strong ? "eqbench.jsonl" : feel ? "goemotions.tsv" : figures ? "questions.jsonl" : "passages.txt",
    arrayBuffer: async () => new TextEncoder()
      .encode(read ? ["Ana", "Ben"].map(subject => JSON.stringify({ kind: "understand", scenario: `${subject}: Our imported fixture.`,
        subject, choices: ["Glad", "Sad"], answer: "Glad", causes: ["A", "B"], cause: "A" })).join("\n") :
        strong ? ["Ana", "Ben"].map((who, index) => JSON.stringify({ text: `${who}: Our imported fixture.`, who,
        emotions: ["Happy", "Sad", "Angry", "Afraid"], scores: index ? [0, 3, 9, 1] : [9, 1, 0, 2] })).join("\n") :
        feel ? "joy\tOur imported fixture.\nanger\tAnother imported fixture.\n" :
        sense ? [0, 1].map(answer => JSON.stringify({ kind: answer ? "social:want" : "social:feel",
        prompt: `Our imported fixture ${answer}.`, ask: "Choose.", options: ["one", "two", "three"], answer })).join("\n") :
        argue ? [0, 1].map(answer => JSON.stringify({ kind: answer ? "formal" : "fallacy",
        prompt: `Our imported fixture ${answer}.`, ask: "Choose.", options: ["one", "two"], answer })).join("\n") :
        lines ? [0, 1].map(answer => JSON.stringify({ kind: "implicature", prompt: `Our imported fixture ${answer}.`,
        ask: "Choose.", options: ["one", "two"], answer })).join("\n") :
        figures ? JSON.stringify({ kind: "metaphor", prompt: "Our imported fixture.", ask: "Choose.",
        options: ["one", "two", "three", "four"], answer: 0 }) :
        "Ada built a wooden boat. Clara painted it bright red.\n".repeat(100)).buffer,
  }];
  await listeners.get("files:change")();
  assert.equal(cacheStatus.textContent, `Using imported ${cacheUnit}.`);
  assert.ok(storage.has(cacheKey));
  assert.equal(options.hidden, false);
  options.elements.rung.value = "4";
  options.elements.rounds.value = "1";
  options.elements.adaptive.checked = false;
  listeners.get("form:submit")({ preventDefault() {} });
  assert.deepEqual(JSON.parse(settings.get(`nw.${task}.options.v1`)), { rung: 4, rounds: 1, adaptive: false });
  const handle = context.ensureMissingWordRun();
  assert.notEqual(oldHandle, handle);
  assert.equal(exports.nw_api_v1_dispatch(handle, 2n, 0n, 0n, 1n, 0n, 0n, 0n, 0n, 0n, 0n), 1n);
  const frame = decode(context.missingWordFrame(true));
  if (figures) assert.ok(frame.some(command => command.text === title));
  else assert.ok(frame.some(command => command.text === "Ada"));
  activeTask = proofreader || figures ? "missing_word" : "proofreader";
  const otherHandle = context.ensureMissingWordRun();
  assert.notEqual(otherHandle, handle);
  assert.equal(context.missingWordInfo(3), 5);
  assert.equal(exports.nw_api_v1_destroy(handle), -1n);
  context.destroyMissingWordRun();
  activeTask = task;
  await listeners.get("clear:click")();
  assert.equal(cacheStatus.textContent, `Using bundled ${cacheUnit}.`);
  assert.equal(storage.has(cacheKey), false);
} finally {
  context.destroyMissingWordRun();
  exports.nw_frame_free(framePtr);
}
console.log(`PASS: ${title} browser option edits, imported ${cacheUnit}, storage, and reset`);
