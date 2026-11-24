import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import { videoJigsawCrop, videoJigsawFramesDiffer } from "../shells/web/video-jigsaw-media.js";

const shell = fileURLToPath(new URL("../shells/web/index.html", import.meta.url));
const source = fs.readFileSync(shell, "utf8");
assert.match(source, /nw_api_v1_task_jigsaw/);
assert.match(source, /return isTaskId\("jigsaw"\)/);
assert.match(source, /function ensureJigsawRun\(\)/);
assert.match(source, /apiCreateRun\(API_TASK\.jigsaw,[\s\S]*options\.puzzles[\s\S]*options\.pieces/);
assert.match(source, /const JIGSAW_PIECE_OPTIONS = Object\.freeze\(\[2, 4, 6, 9, 12/);
assert.match(source, /const defaults = \{ pieces: 9, puzzles: 3, adaptive: true, preview: true,/);
assert.match(source, /options\.markPlaced \? 1n : 0n/);
assert.match(source, /function openJigsawOptions\(returnTo\)/);
assert.match(source, /function applyJigsawOptions\(\)/);
assert.match(source, /function drawJigsawOptionsScreen\(\)/);
assert.match(source, /openingJigsawOptions/);
assert.match(source, /webkitdirectory/);
assert.match(source, /id="jigsaw-photo-clear"/);
assert.match(source, /function importJigsawPhotos\(files\)/);
assert.match(source, /indexedDB\.open\(JIGSAW_PHOTO_DB_NAME/);
assert.match(source, /transaction\.oncomplete = \(\) => resolve\(result\)/);
assert.match(source, /Photo import stopped after \$\{saved\}/);
assert.match(source, /replaceFittedSprite: screen === "task" && isJigsawTask\(\)/);
assert.match(source, /repeats expected/);
assert.match(source, /function jigsawFrame\(black\)/);
assert.match(source, /apiDispatchPointer\(ensureJigsawRun\(\), API_EVENT\.pointerDown/);
const keyboardRoute = source.slice(source.indexOf('    if (isJigsawTask()) {\n      const key = apiKeyFromEvent'),
  source.indexOf('    if (isGoWinningMoveTask())', source.indexOf('    if (isJigsawTask()) {\n      const key = apiKeyFromEvent')));
assert.match(keyboardRoute, /JIGSAW_PHASE\.solving && \(!jigsawCurrentPhotoKey \|\| jigsawActivePhoto\)/);
assert.match(keyboardRoute, /apiDispatchKey\(handle, key, event\)/);
assert.match(keyboardRoute, /scheduleJigsawAdvance\(handle\)/);
assert.match(source, /JIGSAW_ACTION\.start/);
assert.match(source, /if \(isJigsawTask\(\)\) destroyJigsawRun\(\)/);
assert.match(source, /isJigsawTask\(\)/);
assert.match(source, /bytes = jigsawFrame\(dark\(\)\)/);
console.log("jigsaw_browser_contract_test: PASS (source defaults/options, photo persistence/rendering, export, lifecycle, keyboard, pointer, cleanup)");

// Exercise the browser's async photo route and crop with a controllable
// decoder. The WASM smoke separately checks the real fit action.
const photoFunctions = source.slice(source.indexOf("async function selectJigsawPhoto("),
  source.indexOf("function jigsawInfo("));
const requests = [];
const photo = { width: 7, height: 3, image: {} };
const browser = vm.createContext({
  screen: "task", isJigsawTask: () => true, draw() {},
  jigsawPhotoKeys: ["photo"], jigsawShownPhotos: new Set(), jigsawRunHandle: 9n,
  jigsawPhotoLoadGeneration: 0, jigsawActivePhoto: null, jigsawCurrentPhotoKey: "",
  JIGSAW_INFO: { puzzle: 3, phase: 0, trialSide: 2, trialRows: 15 },
  JIGSAW_FIRST_TILE: 3000, JIGSAW_PREVIEW: 5500, PHOTO_JIGSAW_MAX_TILES: 76729, VIDEO_JIGSAW_MAX_TILES: 2552,
  JIGSAW_ACTION: { fitPhoto: 5 },
  JIGSAW_PHOTO_HISTORY_STORAGE: "jigsaw.history", localStorage: { setItem() {} },
  readJigsawPhotoHistory: () => [],
  jigsawInfo: (field) => ({ 3: 1, 0: 1, 2: 2, 15: 3 })[field],
  jigsawPhotoRequest: async () => "blob", decodeJigsawPhoto: async () => photo,
  apiDispatchAction(...args) { requests.push(args); return 1n; },
  closeJigsawPhoto() {},
  clearActiveJigsawPhoto() {
    browser.jigsawPhotoLoadGeneration++;
    browser.jigsawCurrentPhotoKey = "";
    browser.jigsawActivePhoto = null;
  },
});
vm.runInContext(photoFunctions, browser);
await browser.selectJigsawPhoto(1);
assert.deepEqual(requests, [[9n, 5, 3]]);
assert.equal(browser.jigsawActivePhoto, photo);
const draws = [];
const ctx = { save() {}, restore() {}, translate() {}, scale() {},
  drawImage(...args) { draws.push(args); } };
assert.equal(browser.drawJigsawPhotoSprite(ctx,
  { ref: 3005, a: 0, b: 0, c: 120, d: 80 }), true);
assert.deepEqual(draws, [[photo.image, 3, 2, 1, 1, 0, 0, 120, 80]]);
assert.deepEqual(videoJigsawCrop(400, 240), [40, 0, 320, 240]);
assert.deepEqual(videoJigsawCrop(320, 480), [0, 120, 320, 240]);
Object.assign(photo, { clip: true, width: 320, height: 240 });
assert.equal(browser.drawJigsawPhotoSprite(ctx, { ref: 3005, a: 0, b: 0, c: 120, d: 80 }), true);
assert.deepEqual(draws.at(-1), [photo.image, 160, 160, 160, 80, 0, 0, 120, 80]);
assert.equal(browser.drawJigsawPhotoSprite(ctx, { ref: 5500, a: 0, b: 0, c: 120, d: 90 }), true);
assert.deepEqual(draws.at(-1), [photo.image, 0, 0, 320, 240, 0, 0, 120, 90]);
const normalInfo = browser.jigsawInfo;
browser.jigsawInfo = field => ({ 2: 58, 15: 44 })[field];
assert.equal(browser.drawJigsawPhotoSprite(ctx, { ref: 5552, a: 0, b: 0, c: 5, d: 5 }), true);
assert.deepEqual(draws.at(-1), [photo.image, 285, 235, 5, 5, 0, 0, 5, 5]);
browser.jigsawInfo = normalInfo;

Object.assign(photo, { clip: false, width: 7, height: 3 });
browser.apiDispatchAction = (_handle, _action, size) => {
  requests.push(size);
  return size === 0 ? 1n : 2n;
};
let discarded = false;
browser.closeJigsawPhoto = () => { discarded = true; };
await browser.selectJigsawPhoto(1);
assert.equal(discarded, true);
assert.deepEqual(requests.slice(1), [3, 0]);
assert.equal(browser.jigsawCurrentPhotoKey, "");
assert.equal(browser.jigsawActivePhoto, null);
const failedClips = [];
const historyWrites = [];
Object.assign(browser, {
  videoJigsawKeys: ["corrupt-a", "corrupt-b"],
  isVideoJigsawTask: () => true,
  pendingVideoJigsawClip: null, fallbackVideoJigsawClip: null,
  VIDEO_JIGSAW_STORE: "clips",
  VIDEO_JIGSAW_HISTORY_STORAGE: "clips.history",
  localStorage: { setItem(key, value) { historyWrites.push([key, JSON.parse(value)]); } },
  JIGSAW_ACTION: { fitPhoto: 5, videoUnavailable: 6 },
  openVideoJigsawClip() {
    return { ready: Promise.reject(new Error("corrupt")), close() { failedClips.push(true); } };
  },
  apiDispatchAction(...args) { requests.push(args); return 1n; },
});
await browser.selectVideoJigsawClip(1);
assert.equal(failedClips.length, 2);
assert.deepEqual(requests.at(-1), [9n, 6]);
assert.deepEqual(historyWrites.at(-1)[1].sort(), ["corrupt-a", "corrupt-b"]);
assert.equal(browser.jigsawCurrentPhotoKey, "");
assert.match(browser.videoJigsawStatus, /No clip could be played/);
const rgba = value => {
  const frame = new Uint8ClampedArray(320 * 240 * 4).fill(value);
  for (let i = 3; i < frame.length; i += 4) frame[i] = 255;
  return frame;
};
assert.equal(videoJigsawFramesDiffer(rgba(100), rgba(103)), false);
assert.equal(videoJigsawFramesDiffer(rgba(100), rgba(104)), true);

for (const moving of [true, false]) {
  const closed = [];
  const played = [];
  Object.assign(browser, {
    videoJigsawKeys: ["still-a", "still-b", "last-corrupt"],
    Math: { min: Math.min, floor: Math.floor, random: () => 0 },
    jigsawPhotoRequest: async (_mode, operation) => operation({ get: key => key }),
    openVideoJigsawClip(key) {
      return {
        ready: key === "last-corrupt" ? Promise.reject(new Error("corrupt")) : Promise.resolve(),
        hasMotion: async () => moving && key === "still-b",
        play: async () => { played.push(key); },
        close() { closed.push(key); },
        height: 240,
      };
    },
    requestAnimationFrame: () => 1,
  });
  await browser.selectVideoJigsawClip(1);
  assert.deepEqual(played, ["still-b"]);
  assert.deepEqual(closed, moving ? ["still-a"] : ["still-a", "last-corrupt"]);
  assert.equal(browser.jigsawCurrentPhotoKey, "still-b");
  assert.deepEqual(requests.at(-1), [9n, 5, 240]);
}
console.log("PASS: browser Video Jigsaw motion threshold, candidate order, and still-clip fallback");
const optionsSource = source.slice(source.indexOf("function validJigsawPieces("),
  source.indexOf("let jigsawOptions = readJigsawOptions()"));
let saved = { side: 7, puzzles: 5 };
const settings = vm.createContext({
  PHOTO_JIGSAW_MAX_TILES: 76729, VIDEO_JIGSAW_MAX_TILES: 2552, JIGSAW_OPTIONS_STORAGE: "settings",
  VIDEO_JIGSAW_OPTIONS_STORAGE: "video-settings",
  JIGSAW_PUZZLE_OPTIONS: [1, 2, 3, 5],
  localStorage: { getItem: () => JSON.stringify(saved) },
});
vm.runInContext(optionsSource, settings);
assert.equal(settings.readJigsawOptions().pieces, 49);
assert.equal(settings.readJigsawOptions().puzzles, 5);
saved = { pieces: 1000 };
assert.equal(settings.readJigsawOptions().pieces, 1000);
saved = { pieces: 2500 };
assert.equal(settings.readJigsawOptions().pieces, 2500);
assert.equal(settings.readJigsawOptions(true).pieces, 2500);
assert.equal(settings.readJigsawOptions(true).preview, false);
saved = { pieces: 4000 };
assert.equal(settings.readJigsawOptions().pieces, 4000);
console.log("PASS: browser photo sizing, rectangular cropping, and unplayable-photo fallback");
