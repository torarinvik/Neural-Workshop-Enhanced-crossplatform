// Differential harness: the nw-core WASM build vs the Python reference.
//
// Runs the same input grid through the Elisa core compiled to wasm32 and
// through the original bwaccel modules (via a python3 subprocess), and diffs
// the two streams. This is the browser path's equivalent of check.sh.

import fs from "fs";
import { fileURLToPath } from "url";
import { execFileSync } from "child_process";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decode, Kind } from "../shells/web/display-list.js";

// fileURLToPath, not .pathname: the repo path contains spaces.
const WASM = fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));

const MS_GRID = [0, 1, 49, 50, 51, 99, 100, 149, 150, 250, 1050, 2500, 60000];
const TICK_GRID = [0, 1, 10, 50, 100, 250];
const TRIAL_GRID = [100, 500, 1000, 2200, 3000, 4500];
const NBACK_GRID = [1, 2, 3, 5];

function elisaLines(e) {
    const out = [];
    for (const ms of MS_GRID)
        for (const tick of TICK_GRID)
            out.push(`m2t,${ms},${tick},${e.nw_ms_to_ticks(ms, BigInt(tick))}`);

    for (const ms of MS_GRID)
        for (const tick of [1, 50, 100])
            for (const mt of [1, 2, 3, 5])
                out.push(`clamp,${ms},${tick},${mt},` +
                    `${e.nw_clamp_trial_interval_ms(BigInt(ms), BigInt(tick), BigInt(mt), 60000n)}`);

    for (const trial of TRIAL_GRID)
        for (const tick of [1, 100])
            for (let field = 0; field < 7; field++)
                out.push(`ph,${trial},${tick},${field},` +
                    `${e.nw_phase_field(BigInt(trial), 500n, 120n, BigInt(tick), BigInt(field))}`);

    for (const ms of [0, 1, 20, 21, 99, 100, 101, 500, 501, 1999, 2000, 2001, 50000])
        out.push(`step,${ms},${e.nw_interval_adjust_step(BigInt(ms))}`);

    for (const nback of NBACK_GRID)
        for (let x = 0; x < 10; x++)
            out.push(`crab,${nback},${x},${e.nw_crab_back(BigInt(x), BigInt(nback))}`);

    for (const size of [3, 4, 5])
        for (let col = 0; col < size; col++)
            for (let row = 0; row < size; row++)
                out.push(`dist,${size},${col},${row},` +
                    `${e.nw_cell_distance(1n, BigInt(col), BigInt(row), 0n, BigInt(size), 2n)}`);
    return out;
}

const PY = `
import importlib.util, sys
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
base = "/Users/torarinvikbjarko/Documents/Coding Projects/Python Projects/neural-workshop-enhanced/bwaccel/"
sch = load("sch", base + "scheduling.py")
fb  = load("fb",  base + "fallback.py")
out = []
MS = ${JSON.stringify(MS_GRID)}
TICK = ${JSON.stringify(TICK_GRID)}
TRIAL = ${JSON.stringify(TRIAL_GRID)}
NBACK = ${JSON.stringify(NBACK_GRID)}
for ms in MS:
    for tick in TICK:
        out.append("m2t,%d,%d,%d" % (ms, tick, sch.ms_to_ticks(float(ms), tick)))
for ms in MS:
    for tick in (1, 50, 100):
        for mt in (1, 2, 3, 5):
            out.append("clamp,%d,%d,%d,%d" % (ms, tick, mt, sch.clamp_trial_interval_ms(ms, tick, mt, 60000)))
KEYS = ['total_ticks','stimulus_ticks','blank_ticks','feedback_ticks','stimulus_ms','blank_ms','feedback_ms']
for trial in TRIAL:
    for tick in (1, 100):
        p = sch.plan_trial_phases(trial, 500, 120, tick)
        for field, key in enumerate(KEYS):
            out.append("ph,%d,%d,%d,%d" % (trial, tick, field, p[key]))
for ms in (0,1,20,21,99,100,101,500,501,1999,2000,2001,50000):
    out.append("step,%d,%d" % (ms, sch.interval_adjust_step(ms)))
for nback in NBACK:
    for x in range(10):
        out.append("crab,%d,%d,%d" % (nback, x, fb._crab_back(x, nback)))
for size in (3, 4, 5):
    for col in range(size):
        for row in range(size):
            dx = 2*col - (size-1); dy = 2*row - (size-1)
            out.append("dist,%d,%d,%d,%d" % (size, col, row, dx*dx + dy*dy))
print("\\n".join(out))
`;

const { exports, instance } = await instantiateElisa(fs.readFileSync(WASM), { warn: false });
const got = elisaLines(exports);
const want = execFileSync("python3", ["-c", PY], { encoding: "utf8" })
    .trim().split("\n");

if (got.length !== want.length) {
    console.log(`FAIL: ${got.length} lines vs ${want.length}`);
    process.exit(1);
}
const bad = got.map((g, i) => [i, g, want[i]]).filter(([, g, w]) => g !== w);
for (const [i, g, w] of bad.slice(0, 10)) {
    console.log(`MISMATCH line ${i}\n  wasm:   ${g}\n  python: ${w}`);
}
if (bad.length) {
    console.log(`FAIL: ${bad.length}/${want.length} mismatches`);
    process.exit(1);
}
console.log(`PASS: ${want.length} cases identical`);

// The shell-facing session export must use the same generator as the core
// sweep, not the old hand-written position walk. Decode the emitted scene and
// recover its 3x3 position so this checks the complete ABI path without making
// the browser harness depend on an internal struct layout.
const SESSION_MODES = [2, 3, 4, 5, 7, 8, 20, 21, 100, 107, 130, 258];
const SESSION_BACKS = [1, 2, 3, 5];
const SESSION_SEEDS = [1, 7, 12345];
const SESSION_TRIALS = [1, 2, 5, 11, 18];
const SESSION_PY = `
import sys
sys.path.insert(0, "test")
import sessionapp_diff
case = 0
for mode in ${JSON.stringify(SESSION_MODES)}:
    for back in ${JSON.stringify(SESSION_BACKS)}:
        for seed in ${JSON.stringify(SESSION_SEEDS)}:
            for trial in ${JSON.stringify(SESSION_TRIALS)}:
                row = sessionapp_diff.one(case, seed, trial, mode, back)
                print("|".join(str(x) for x in row))
                case += 1
`;
const sessionWant = execFileSync("python3", ["-c", SESSION_PY], { encoding: "utf8" })
    .trim().split("\n");
const sessionPtr = Number(exports.nw_frame_alloc(65536n));
const positionMap = [
    [2, 1], [0, 1], [1, 2], [2, 2],
    [0, 2], [1, 0], [2, 0], [0, 0], [1, 1],
];
function positionFromFrame(bytes) {
    const stimulus = decode(bytes).find(c => c.kind === Kind.RECT &&
        c.color === 0x0084ffff && c.c < 120);
    if (!stimulus) return 0;
    const extent = 340 / 3;
    const inset = extent * 0.12;
    const col = Math.round((stimulus.a - (286 + inset)) / extent);
    const row = Math.round(((420 + inset) - stimulus.b) / extent);
    return positionMap.findIndex(([x, y]) => x === col && y === row) + 1;
}
let sessionBad = 0;
let sessionCase = 0;
for (const mode of SESSION_MODES) {
    for (const back of SESSION_BACKS) {
        for (const seed of SESSION_SEEDS) {
            for (const trial of SESSION_TRIALS) {
                const length = Number(exports.nw_session_frame_write(
                    BigInt(sessionPtr), 65536n, BigInt(trial), BigInt(back),
                    BigInt(seed), BigInt(mode), -1n));
                const bytes = new Uint8Array(instance.exports.memory.buffer, sessionPtr, length);
                const actual = positionFromFrame(bytes);
                const expected = Number(sessionWant[sessionCase].split("|")[7]);
                if (actual !== expected) {
                    if (sessionBad < 10) {
                        console.log(`SESSION MISMATCH case ${sessionCase}: ` +
                            `wasm position ${actual}, python position ${expected}`);
                    }
                    sessionBad++;
                }
                sessionCase++;
            }
        }
    }
}
if (sessionBad) {
    console.log(`FAIL: ${sessionBad}/${sessionCase} session frame mismatches`);
    process.exit(1);
}
console.log(`PASS: ${sessionCase} session frame cases identical`);

// The complete host-facing composition has a wider ABI than the compact
// session generator above. Exercise each branch that the batch sweep covers,
// including the pooled marker (which is intentionally invisible to the text
// recorder but is consumed by the browser shell).
const batchPtr = Number(exports.nw_frame_alloc(65536n));
function batchFrame(trial, mode, black, started, hideText, paused,
                    grid3d, expanded, gridlines, oldStyle, sharpCorners,
                    sessionNumber, verdict, inputAnswer) {
    const length = Number(exports.nw_batch_write(
        BigInt(batchPtr), 65536n, BigInt(trial), 2n, 7n, BigInt(mode),
        BigInt(black), BigInt(started), BigInt(hideText), BigInt(paused),
        BigInt(grid3d), BigInt(expanded), BigInt(gridlines), BigInt(oldStyle),
        BigInt(sharpCorners), BigInt(sessionNumber), BigInt(verdict),
        BigInt(inputAnswer)));
    return new Uint8Array(instance.exports.memory.buffer, batchPtr, length).slice();
}

const batchCases = [
    [1, 2, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, -1, 0],
    [2, 2, 0, 1, 0, 0, 0, 0, 1, 1, 1, 0, -1, 0],
    [3, 7, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, -1, 0],
    [1, 21, 1, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0],
    [2, 258, 0, 1, 0, 0, 1, 0, 1, 0, 0, 0, -1, 0],
    [5, 2, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, -1, 0],
];
let batchBad = 0;
for (const [trial, mode, black, started, hideText, paused, grid3d,
            expanded, gridlines, oldStyle, sharpCorners, sessionNumber,
            verdict, inputAnswer] of batchCases) {
    const commands = decode(batchFrame(trial, mode, black, started, hideText,
                                        paused, grid3d, expanded, gridlines,
                                        oldStyle, sharpCorners, sessionNumber,
                                        verdict, inputAnswer));
    const fail = (message) => {
        if (batchBad < 8) console.log(`BATCH MISMATCH mode ${mode}: ${message}`);
        batchBad++;
    };
    if (!commands.length || commands[0].kind !== Kind.RECT) fail("no background");
    if (commands[0]?.color !== (black ? 0x000000ff : 0xffffffff)) fail("bad background");
    if (commands.at(-1)?.kind !== Kind.MARKER || commands.at(-1)?.text !== "frame-end") {
        fail("missing frame marker");
    }
    if (!commands.some(c => c.kind === Kind.TEXT)) fail("no text commands");
    const texts = commands.filter(c => c.kind === Kind.TEXT).map(c => c.text);
    if (started && !hideText && !texts.some(t => t.includes("remaining"))) {
        fail("missing countdown");
    }
    if (started && mode === 7 && !hideText && !texts.includes("Answer: 0")) {
        fail("missing arithmetic answer");
    }
    if (started && mode === 21 && !commands.some(c => c.kind === Kind.SPRITE)) {
        fail("missing image sprite reference");
    }
    if (started && mode === 2 && oldStyle && !commands.some(c => c.kind === Kind.POLYGON)) {
        fail("missing old-style polygon");
    }
    if (started && grid3d && (!commands.some(c => c.kind === Kind.POLYGON) ||
                              !commands.some(c => c.kind === Kind.LINE))) {
        fail("missing 3D stage or pattern");
    }
}
if (batchBad) {
    console.log(`FAIL: ${batchBad}/${batchCases.length} batch ABI cases failed`);
    process.exit(1);
}
console.log(`PASS: ${batchCases.length} batch ABI cases validated`);

// Menu editing is also host state, not just a moving marker. Verify that the
// scalar menu ABI carries changed booleans and cycler values into the frame.
const menuPtr = Number(exports.nw_frame_alloc(65536n));
function menuState(selpos, black, bools, cubes, grid, activeCells, trialMs,
                   multi, multimode, interferenceTenths) {
    const length = Number(exports.nw_menu_state_write(
        BigInt(menuPtr), 65536n, BigInt(selpos), BigInt(black), BigInt(bools),
        BigInt(cubes), BigInt(grid), BigInt(activeCells), BigInt(trialMs),
        BigInt(multi), BigInt(multimode), BigInt(interferenceTenths)));
    return new Uint8Array(instance.exports.memory.buffer, menuPtr, length).slice();
}
const menuCases = [
    [0, 0, 1, 1, 3, 8, 10, 1, 0, 125],
    [7, 0, (1 << 0) | (1 << 1) | (1 << 7), 6, 8, 0, 500, 4, 1, 1000],
    [23, 1, (1 << 5) | (1 << 9) | (1 << 10), 2, 5, 16, 250, 2, 1, 0],
];
let menuBad = 0;
for (const args of menuCases) {
    const commands = decode(menuState(...args));
    const texts = commands.filter(c => c.kind === Kind.TEXT).map(c => c.text);
    const fail = (message) => {
        if (menuBad < 8) console.log(`MENU MISMATCH row ${args[0]}: ${message}`);
        menuBad++;
    };
    if (commands[0]?.color !== (args[1] ? 0x000000ff : 0xffffffff)) fail("bad background");
    if (commands.at(-1)?.kind !== Kind.MARKER) fail("missing frame marker");
    if (args[2] & (1 << 1) && !texts.some(t => t.startsWith("Use color") && t.endsWith("Yes"))) {
        fail("changed boolean did not render");
    }
    if (!texts.some(t => t.startsWith("Cubes in 3D pattern") && t.trimEnd().endsWith(String(args[3])))) {
        fail("changed integer did not render");
    }
    if (args[8] && !texts.some(t => t.includes("differentiated by") && t.endsWith("image"))) {
        fail("changed text cycler did not render");
    }
}
if (menuBad) {
    console.log(`FAIL: ${menuBad}/${menuCases.length} menu ABI cases failed`);
    process.exit(1);
}
console.log(`PASS: ${menuCases.length} menu ABI cases validated`);

// The title's Space action lands on the all-games task hub. Check the shell
// ABI across categories, selections, and both canvas themes so the route is
// covered independently of the browser's event wiring.
const taskhubPtr = Number(exports.nw_frame_alloc(65536n));
function taskhubFrame(category, selected, black) {
    const length = Number(exports.nw_taskhub_write(
        BigInt(taskhubPtr), 65536n, BigInt(category), BigInt(selected),
        BigInt(black), 912n, 684n));
    return new Uint8Array(instance.exports.memory.buffer, taskhubPtr, length).slice();
}
const taskhubCases = [
    [0, 0, 0, "Working memory", "N-Back"],
    [2, 4, 0, "Attention", "Pursuit"],
    [4, 10, 1, "Reasoning", "Numberology"],
    [6, 0, 0, "Self-control", "Cookie Thief"],
];
let taskhubBad = 0;
for (const [category, selected, black, categoryName, taskName] of taskhubCases) {
    const commands = decode(taskhubFrame(category, selected, black));
    const texts = commands.filter(c => c.kind === Kind.TEXT).map(c => c.text);
    const fail = (message) => {
        if (taskhubBad < 8) console.log(`TASKHUB MISMATCH category ${category}: ${message}`);
        taskhubBad++;
    };
    if (!texts.includes("Choose a task")) fail("missing title");
    if (!texts.includes(categoryName)) fail("missing category tab");
    if (!texts.includes(taskName)) fail("missing selected task");
    if (!commands.some(c => c.kind === Kind.RECT && c.color === 0x4060ffff)) {
        fail("missing selected accent card");
    }
}
if (taskhubBad) {
    console.log(`FAIL: ${taskhubBad}/${taskhubCases.length} task hub ABI cases failed`);
    process.exit(1);
}
console.log(`PASS: ${taskhubCases.length} task hub ABI cases validated`);
