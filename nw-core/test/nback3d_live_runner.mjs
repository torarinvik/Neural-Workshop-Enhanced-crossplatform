// Companion runner for nback3d_live_diff.py.  It drives only the public
// versioned 3D N-Back API and echoes the source oracle with observed state,
// feedback, and final counters filled in.
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";

const wasm = process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url));
const { exports, instance } = await instantiateElisa(fs.readFileSync(wasm), { warn: false });
const TASK = BigInt(exports.nw_api_v1_task_nback_3d());
const EVENT_ACTION = 1n;
const ACTION = Object.freeze({ start: 0n, match: 1n, tick: 2n });
const FIELD = Object.freeze({ phase: 0, trial: 2, position: 5, color: 6,
  verdict: 7, hits: 9, misses: 10, falseAlarms: 11, correctRejections: 12 });
const PHASE = Object.freeze({ stimulus: 1n, response: 2n, feedback: 3n, done: 4n });
const STATUS = Object.freeze({ accepted: 1n });
const statePtr = Number(exports.nw_frame_alloc(112n));

function create(options, seed) {
  return exports.nw_api_v1_create(TASK, 1n, ...options, BigInt(seed));
}

function state(handle) {
  assertSize(exports.nw_api_v1_read_state(handle, BigInt(statePtr), 112n));
  const view = new DataView(instance.exports.memory.buffer, statePtr, 112);
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function assertSize(value) {
  if (value !== 112n) throw new Error(`state size ${value}`);
}

function action(handle, code, timestamp, sequence) {
  return exports.nw_api_v1_dispatch(handle, EVENT_ACTION,
    BigInt(timestamp), BigInt(sequence), code, 0n, 0n, 0n, 0n, 0n, 0n);
}

function advance(handle, timestamp, elapsed, sequence) {
  return exports.nw_api_v1_advance(handle, BigInt(timestamp), BigInt(elapsed),
    BigInt(sequence));
}

function runCase(source) {
  const total = BigInt(source.total);
  const handle = create([BigInt(source.nback), BigInt(source.cubes), total,
    3000n, 500n, 200n], source.seed);
  if (handle <= 0n) throw new Error(`create failed for seed ${source.seed}`);
  if (action(handle, ACTION.start, 0, 0) !== STATUS.accepted) {
    throw new Error(`start rejected for seed ${source.seed}`);
  }
  if (advance(handle, 1000, 1000, 1) !== STATUS.accepted) {
    throw new Error(`startup advance rejected for seed ${source.seed}`);
  }

  const trials = [];
  for (let index = 0; index < source.total; index += 1) {
    const trialStart = 1000 + index * 3000;
    let values = state(handle);
    if (values[FIELD.phase] !== PHASE.stimulus ||
        values[FIELD.trial] !== BigInt(index + 1)) {
      throw new Error(`stimulus state mismatch at ${source.seed}/${index}`);
    }
    const pressed = Boolean(source.presses[index]);
    if (pressed && action(handle, ACTION.match, trialStart + 100,
                          2 + index * 4) !== STATUS.accepted) {
      throw new Error(`match rejected at ${source.seed}/${index}`);
    }
    const position = values[FIELD.position];
    const color = values[FIELD.color];
    if (advance(handle, trialStart + 500, 500, 3 + index * 4) !== STATUS.accepted ||
        advance(handle, trialStart + 2800, 2300, 4 + index * 4) !== STATUS.accepted) {
      throw new Error(`phase advance rejected at ${source.seed}/${index}`);
    }
    values = state(handle);
    if (values[FIELD.phase] !== PHASE.feedback) {
      throw new Error(`feedback state mismatch at ${source.seed}/${index}`);
    }
    const verdict = values[FIELD.verdict] === 1n ? "hit" :
      values[FIELD.verdict] === 0n ? "false_alarm" :
      values[FIELD.verdict] === 2n ? "miss" : "correct_rejection";
    trials.push({ position: Number(position), color: Number(color),
      match: source.trials[index].match, pressed, verdict });
    if (index + 1 < source.total &&
        advance(handle, trialStart + 3000, 200, 5 + index * 4) !== STATUS.accepted) {
      throw new Error(`next-trial advance rejected at ${source.seed}/${index}`);
    }
  }
  const finalDeadline = 1000 + (source.total - 1) * 3000 + 3000;
  if (advance(handle, finalDeadline, 200, 5 + (source.total - 1) * 4) !== STATUS.accepted) {
    throw new Error(`final completion advance rejected for seed ${source.seed}`);
  }
  const values = state(handle);
  if (values[FIELD.phase] !== PHASE.done) {
    throw new Error(`completion state mismatch for seed ${source.seed}`);
  }
  const counts = {
    hits: Number(values[FIELD.hits]),
    misses: Number(values[FIELD.misses]),
    false_alarms: Number(values[FIELD.falseAlarms]),
    correct_rejections: Number(exports.nw_api_v1_nback3d_info(handle, 12n)),
  };
  exports.nw_api_v1_destroy(handle);
  return { ...source, trials, counts: { ...source.counts, ...counts } };
}

const input = await new Promise((resolve, reject) => {
  let data = "";
  process.stdin.setEncoding("utf8");
  process.stdin.on("data", (chunk) => { data += chunk; });
  process.stdin.on("end", () => resolve(data));
  process.stdin.on("error", reject);
});
const cases = JSON.parse(input);
const output = cases.map(runCase);
process.stdout.write(JSON.stringify(output));
