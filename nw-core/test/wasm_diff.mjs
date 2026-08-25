// Differential harness: the nw-core WASM build vs the Python reference.
//
// Runs the same input grid through the Elisa core compiled to wasm32 and
// through the original bwaccel modules (via a python3 subprocess), and diffs
// the two streams. This is the browser path's equivalent of check.sh.

import fs from "fs";
import { fileURLToPath } from "url";
import { execFileSync } from "child_process";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

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

const { exports } = await instantiateElisa(fs.readFileSync(WASM), { warn: false });
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
