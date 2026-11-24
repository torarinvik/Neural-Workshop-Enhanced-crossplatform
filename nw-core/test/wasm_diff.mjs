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
const WASM = process.env.NWCORE_WASM_PATH ??
    fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));

const REFERENCE_BWACCEL = fileURLToPath(
    new URL("../../original-neural-workshop-enhanced/bwaccel/", import.meta.url));

const MS_GRID = [0, 1, 49, 50, 51, 99, 100, 149, 150, 250, 1050, 2500, 60000];
const TICK_GRID = [0, 1, 10, 50, 100, 250];
const TRIAL_GRID = [100, 500, 1000, 2200, 3000, 4500];

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
base = ${JSON.stringify(REFERENCE_BWACCEL)}
sch = load("sch", base + "scheduling.py")
out = []
MS = ${JSON.stringify(MS_GRID)}
TICK = ${JSON.stringify(TICK_GRID)}
TRIAL = ${JSON.stringify(TRIAL_GRID)}
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
for size in (3, 4, 5):
    for col in range(size):
        for row in range(size):
            dx = 2*col - (size-1); dy = 2*row - (size-1)
            out.append("dist,%d,%d,%d,%d" % (size, col, row, dx*dx + dy*dy))
print("\\n".join(out))
`;

const { exports, instance, stubbed } = await instantiateElisa(fs.readFileSync(WASM), { warn: false });
const requiredProfilerImports = [
    "elisa_profile_allocation_negotiate",
    "elisa_profile_region_layout_negotiate",
    "elisa_profile_region_layout_v1",
    "elisa_profile_allocation_event_v1",
];
const missingProfilerImports = requiredProfilerImports.filter((name) => stubbed.includes(name));
if (missingProfilerImports.length) {
    throw new Error(`WASM host profiler ABI is incomplete: ${missingProfilerImports.join(", ")}`);
}
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
    [0, 0, 0, "Working memory", "3D N-Back"],
    [2, 4, 0, "Attention", "Pursuit"],
    [4, 2, 0, "Reasoning", "Hidden Rule"],
    [4, 3, 0, "Reasoning", "Hidden Wiring"],
    [4, 5, 0, "Reasoning", "Video Jigsaw"],
    [4, 6, 0, "Reasoning", "Video Sequence"],
    [4, 14, 1, "Reasoning", "Numberology"],
    [6, 0, 0, "Self-control", "Cookie Thief"],
    [6, 1, 0, "Self-control", "Delay"],
    [7, 0, 0, "Decisions", "Triage"],
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
