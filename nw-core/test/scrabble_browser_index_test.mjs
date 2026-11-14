import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const root = fileURLToPath(new URL("..", import.meta.url));
const wasm = process.env.NWCORE_WASM_PATH ?? `${root}/build/nwcore.wasm`;
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const html = fs.readFileSync(`${root}/shells/web/index.html`, "utf8");
const validation = html.slice(html.indexOf("function attachScrabbleIndex("), html.indexOf("function crosswordIndexRequest("));
const install = html.slice(html.indexOf("function installCrosswordIndex("), html.indexOf("async function restoreCrosswordIndex("));
const context = vm.createContext({ exports, instance, Uint8Array, Number, BigInt, Error,
  API_TASK: {scrabble: BigInt(exports.nw_api_v1_task_scrabble()), crossword: BigInt(exports.nw_api_v1_task_crossword())},
  apiCreateRun: (task, options, seed) => exports.nw_api_v1_create(task, 1n, ...options, seed),
  apiDestroyRun: handle => exports.nw_api_v1_destroy(handle),
  isCrosswordTask: () => true, isScrabbleTask: () => false,
});
vm.runInContext(`let crosswordRunHandle = 0n, scrabbleRunHandle = 0n;
let crosswordIndexBytes = null, crosswordIndexForCrossword = false, crosswordIndexForScrabble = false;
let crosswordIndexNotice = "Lexicon ready"; ${validation}\n${install}`, context);
const installIndex = (text, required) => context.installCrosswordIndex(new TextEncoder().encode(text), required);
const flags = () => vm.runInContext("[crosswordIndexForCrossword, crosswordIndexForScrabble]", context).join(",");
installIndex("cat\t1\t\ndog\t2\t\n", "scrabble");
assert.equal(flags(), "false,true", "unclued words are accepted for Scrabble only");
assert.match(context.crosswordIndexStatus(), /no usable clues/);
assert.throws(() => installIndex("cat\t1\t\ndog\t2\t\n", "crossword"));
assert.equal(flags(), "false,true", "failed replacement preserves the prior index");
installIndex("cat\t1\tfeline\ndog\t2\tcanine\n", "crossword");
assert.equal(flags(), "true,true", "clued index remains shared");
assert.throws(() => installIndex("not an index\n", "scrabble"));
assert.equal(flags(), "true,true");
installIndex("cat\t1\t\ndog\t2\t\n", null);
assert.equal(flags(), "false,true", "restoring a saved Scrabble-only index succeeds");
console.log("scrabble_browser_index_test: PASS (per-game validation, replacement, restore)");
