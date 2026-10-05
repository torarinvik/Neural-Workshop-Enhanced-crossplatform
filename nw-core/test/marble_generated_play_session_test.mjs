// Generated-board Marble play sessions.
//
// The board generator is a certified cell maze. Reconstructing the open-cell
// route from its transported wall strips gives this test a deterministic held
// input trace without embedding a board fixture or bypassing the physics. The
// route is only a test driver: production input remains ordinary key events.
// The selected cases intentionally include both physical wins and swallowed
// marbles so the controller's REPORT/RECORD_RESULT boundary is exercised in
// both directions.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import fs from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decodeMarbleBoard } from "../shells/web/marble-maze.js";
import { loadMarbleMazeMuJoCo } from "../shells/web/marble-maze-mujoco.js";
import { captureIntegrator } from "./marble_integrator_capture.mjs";

const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");
const wasmPath = resolve(process.env.NWCORE_WASM_PATH ??
  fileURLToPath(new URL("../build/nwcore.wasm", import.meta.url)));
const coreWasmBytes = fs.readFileSync(wasmPath);
const { exports, instance } = await instantiateElisa(coreWasmBytes, {
  warn: false,
});
const experimentalMuJoCoModule = process.env.NW_MUJOCO_WASM_MODULE;
const experimentalMuJoCoPath = experimentalMuJoCoModule
  ? resolve(experimentalMuJoCoModule) : null;
const repositoryRoot = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const manifestPath = resolve(repositoryRoot,
  "nw-core/docs/marble-physics-manifest.json");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const expectedRuntime = Object.fromEntries(
  manifest.browser.runtimeFiles.map((entry) => [entry.path, entry]));
const maintainedMuJoCoModulePath = resolve(repositoryRoot,
  "nw-core/shells/web/vendor/mujoco/mujoco.js");
const mujocoModulePath = experimentalMuJoCoPath ?? maintainedMuJoCoModulePath;
const mujocoWasmPath = resolve(dirname(mujocoModulePath), "mujoco.wasm");
const mujocoModuleBytes = fs.readFileSync(mujocoModulePath);
const mujocoWasmBytes = fs.readFileSync(mujocoWasmPath);
const coreWasmRealPath = fs.realpathSync(wasmPath);
const mujocoModuleRealPath = fs.realpathSync(mujocoModulePath);
const mujocoWasmRealPath = fs.realpathSync(mujocoWasmPath);
const expectedMujocoJs = expectedRuntime[
  "nw-core/shells/web/vendor/mujoco/mujoco.js"];
const expectedMujocoWasm = expectedRuntime[
  "nw-core/shells/web/vendor/mujoco/mujoco.wasm"];
assert.ok(expectedMujocoJs && expectedMujocoWasm,
  "physics manifest must identify both maintained MuJoCo runtime files");
const runtimeProvenance = {
  schema: "neural-workshop.marble-runtime-provenance.v1",
  adapterFiles: ["marble-maze-mujoco.js", "marble-maze.js", "python-hypot.js"].map(name => {
    const path = resolve(repositoryRoot, "nw-core/shells/web", name);
    return { path: fs.realpathSync(path), sha256: sha256(fs.readFileSync(path)) };
  }),
  coreWasm: {
    path: coreWasmRealPath,
    sha256: sha256(coreWasmBytes),
  },
  mujoco: {
    jsPath: mujocoModuleRealPath,
    jsSha256: sha256(mujocoModuleBytes),
    wasmPath: mujocoWasmRealPath,
    wasmSha256: sha256(mujocoWasmBytes),
    wasmResolution: "Emscripten import.meta.url resolves adjacent mujoco.wasm",
    maintainedFilesMatchManifest:
      mujocoModuleRealPath === fs.realpathSync(resolve(repositoryRoot,
        expectedMujocoJs.path)) &&
      mujocoWasmRealPath === fs.realpathSync(resolve(repositoryRoot,
        expectedMujocoWasm.path)) &&
      sha256(mujocoModuleBytes) === expectedMujocoJs.sha256 &&
      sha256(mujocoWasmBytes) === expectedMujocoWasm.sha256,
  },
  traceHarness: {
    path: fs.realpathSync(fileURLToPath(import.meta.url)),
    sha256: sha256(fs.readFileSync(fileURLToPath(import.meta.url))),
  },
  node: process.version,
};
if (!experimentalMuJoCoPath) {
  assert.equal(runtimeProvenance.mujoco.maintainedFilesMatchManifest, true,
    "default MuJoCo JS/WASM pair must match the maintained physics manifest");
}
const Game = await loadMarbleMazeMuJoCo(experimentalMuJoCoModule
  ? async () => {
    const module = await import(pathToFileURL(experimentalMuJoCoPath).href);
    return module.default();
  }
  : undefined);

const TASK_MARBLE = 642986n;
const STATUS = Object.freeze({ accepted: 1n });
const EVENT = Object.freeze({ action: 1n, keyDown: 2n, keyUp: 3n });
const ACTION = Object.freeze({
  start: 0n,
  level: 2n,
  report: 3n,
  syncSettleTime: 11n,
  recordResult: 12n,
  score: 10n,
});
const KEY = Object.freeze({ W: 3n, N: 4n, E: 5n, S: 6n });
const PHASE = Object.freeze({ running: 1n, feedback: 2n, done: 4n });
const INFO = Object.freeze({ phase: 0, rung: 1, trial: 2, seed: 5, elapsedMs: 6 });
const RESULT = Object.freeze({
  rung: 100n,
  elapsedMs: 101n,
  home: 102n,
  lost: 103n,
  verdict: 104n,
  scoreWin: 105n,
  boardSeed: 106n,
});
const STATE_BYTES = 112n;
const STATE_POINTER = Number(exports.nw_frame_alloc(STATE_BYTES));
const BOARD_CAPACITY = 65536n;
const BOARD_POINTER = Number(exports.nw_frame_alloc(BOARD_CAPACITY));
assert.ok(STATE_POINTER > 0 && BOARD_POINTER > 0,
  "WASM test buffers could not be allocated");

function readState(handle) {
  const length = exports.nw_api_v1_read_state(
    handle, BigInt(STATE_POINTER), STATE_BYTES);
  assert.equal(length, STATE_BYTES);
  const view = new DataView(
    instance.exports.memory.buffer, STATE_POINTER, Number(length));
  return Array.from({ length: 12 }, (_, index) =>
    view.getBigInt64(16 + index * 8, true));
}

function boardForState(state) {
  const length = Number(exports.nw_marble_board_write(
    BigInt(BOARD_POINTER), BOARD_CAPACITY,
    state[INFO.rung], state[INFO.seed]));
  assert.ok(length > 0, "WASM did not produce the controller's board");
  return decodeMarbleBoard(new Uint8Array(
    instance.exports.memory.buffer, BOARD_POINTER, length));
}

function resultValue(handle, field) {
  return exports.nw_api_v1_marble_value(handle, field, 0n);
}

function noSlipCostChangeProbes(mujoco, values) {
  const probes = [];
  let offset = 0;
  while (offset < values.length) {
    const island = Number(values[offset]);
    const iteration = Number(values[offset + 1]);
    const row = Number(values[offset + 2]);
    const dim = Number(values[offset + 3]);
    const tangent = dim - 1;
    const width = 12 + 7 * tangent + tangent * tangent;
    if (tangent < 0 || offset + width > values.length) break;
    let cursor = offset + 11;
    const residual = values.slice(cursor, cursor += tangent);
    const oldForce = values.slice(cursor, cursor += tangent);
    const matrix = values.slice(cursor, cursor += tangent * tangent);
    cursor += tangent; // rhs
    const newForce = values.slice(cursor, cursor += tangent);
    const actualChange = values[cursor++];
    const delta = newForce.map((value, index) => value - oldForce[index]);
    const quadratic = Number(mujoco.mju_mulVecMatVec(delta, matrix, delta));
    const linear = Number(mujoco.mju_dot(delta, residual));
    probes.push({ island, iteration, row, quadratic, linear,
      change: 0.5 * quadratic + linear, actualChange });
    offset += width;
  }
  return probes;
}

function noSlipIteration1DotProbes(mujoco, inputStates, iterationTrace,
                                   contactTrace) {
  const states = new Map(inputStates.map((state) => [Number(state.island), state]));
  const iterationZeroForces = new Map();
  for (let offset = 0; offset + 6 <= iterationTrace.length;) {
    const island = Number(iterationTrace[offset]);
    const iteration = Number(iterationTrace[offset + 1]);
    const count = Number(iterationTrace[offset + 2]);
    const width = 6 + 3 * count;
    if (count < 0 || offset + width > iterationTrace.length) break;
    if (iteration === 0) {
      const forces = new Map();
      for (let index = 0; index < count; index += 1) {
        const cursor = offset + 6 + 3 * index;
        forces.set(Number(iterationTrace[cursor]),
          Number(iterationTrace[cursor + 1]));
      }
      iterationZeroForces.set(island, forces);
    }
    offset += width;
  }

  const firstContactByIsland = new Map();
  for (let offset = 0; offset + 6 <= contactTrace.length;) {
    const island = Number(contactTrace[offset]);
    const iteration = Number(contactTrace[offset + 1]);
    const row = Number(contactTrace[offset + 2]);
    const dimension = Number(contactTrace[offset + 3]);
    const tangent = dimension - 1;
    const width = 12 + 7 * tangent + tangent * tangent;
    if (tangent < 0 || offset + width > contactTrace.length) break;
    if (iteration === 1 && !firstContactByIsland.has(island)) {
      firstContactByIsland.set(island, { offset, row, dimension, tangent });
    }
    offset += width;
  }

  const probes = [];
  for (const [island, contact] of firstContactByIsland) {
    const state = states.get(island);
    if (!state || !state.arAvailable) continue;
    const nefc = Number(state.nefc);
    const force = Array.from(state.force, Number);
    for (const [row, value] of iterationZeroForces.get(island) ?? []) {
      force[row] = value;
    }
    const capturedResidualOffset = contact.offset + 11;
    const capturedResidual = Array.from(
      contactTrace.slice(capturedResidualOffset,
        capturedResidualOffset + contact.tangent), Number);
    const rows = [];
    for (let tangentIndex = 0; tangentIndex < contact.tangent;
         tangentIndex += 1) {
      const row = contact.row + 1 + tangentIndex;
      const matrixRow = Array.from(
        state.AR.slice(row * nefc, (row + 1) * nefc), Number);
      const dot = Number(mujoco.mju_dot(matrixRow, force));
      const regularizerProduct = Number(state.R[row]) * force[row];
      rows.push({
        row,
        b: Number(state.b[row]),
        dot,
        regularizerProduct,
        separatelyRoundedResidual:
          Number(state.b[row]) + dot - regularizerProduct,
        capturedResidual: capturedResidual[tangentIndex],
      });
    }
    probes.push({ island, row: contact.row, dimension: contact.dimension, rows });
  }
  return probes;
}

const engineDiagnosticEvents = new Set(
  (process.env.NW_MARBLE_PLAY_TRACE_ENGINE_EVENTS ?? "")
    .split(",").filter(Boolean).map(Number));
const engineDiagnosticFields = [
  "cvel", "cdof", "cdof_dot", "cacc", "cfrc_ext", "cfrc_int",
  "cinert", "crb", "subtree_com",
  "xpos", "xquat", "xipos", "ximat",
  // Match the solver's packed mass matrix and sparse Jacobian layout too:
  // Newton initializes Ma/Jaref from these before its first trace record.
  "M", "qLD", "qLDiagInv",
  // Keep island-local solver vectors and both reverse maps so a synchronized
  // Newton solve can be checked through its gather/scatter boundary.
  "iacc", "iacc_smooth", "ifrc_constraint", "ifrc_smooth",
  "island_nv", "island_nefc", "map_efc2iefc",
  "qpos", "qvel", "qacc", "qacc_smooth", "qacc_warmstart",
  "qfrc_constraint", "qfrc_smooth", "qfrc_bias", "qfrc_passive",
  "qfrc_applied", "qH", "qHDiagInv", "qLDiagInv", "qDeriv",
  "efc_force", "efc_pos", "efc_vel", "efc_aref", "efc_b", "efc_state",
  "efc_D", "efc_R", "efc_KBIP", "efc_margin", "efc_diagA",
  "efc_type", "efc_id", "efc_island", "efc_frictionloss",
  "efc_J", "efc_AR",
  "efc_KBIP", "efc_D", "efc_R",
  "efc_J_rownnz", "efc_J_rowadr", "efc_J_rowsuper", "efc_J_colind",
  "map_idof2dof", "map_dof2idof", "map_iefc2efc",
  "iefc_D", "iefc_R", "iefc_frictionloss", "iefc_type", "iefc_id",
  "iefc_state", "iefc_force", "iefc_aref",
  "island_idofadr", "island_iefcadr",
  "solver_niter", "solver_nnz", "solver_fwdinv", "geom_xpos", "geom_xmat",
];
const solverOutputFields = new Set([
  "efc_b", "efc_force", "efc_state", "iacc", "iacc_smooth",
  "ifrc_constraint", "ifrc_smooth", "iefc_D", "iefc_R",
  "iefc_frictionloss", "iefc_type", "iefc_id", "iefc_state",
  "iefc_force", "iefc_aref", "solver_niter", "solver_nnz",
  "solver_fwdinv", "solver_stats", "qacc", "qfrc_constraint",
]);
const solverInputTracePath = process.env.NW_MARBLE_SYNC_SOLVER_INPUT_TRACE;
const solverInputTraceEvent = Number(
  process.env.NW_MARBLE_SYNC_SOLVER_INPUT_EVENT ?? "-1");
const solverInputTraceSubstep = Number(
  process.env.NW_MARBLE_SYNC_SOLVER_INPUT_SUBSTEP ?? "0");
const solverInputTraceOutput = process.env.NW_MARBLE_SYNC_SOLVER_OUTPUT_PATH;
const solverInputReference = solverInputTracePath
  ? JSON.parse(fs.readFileSync(solverInputTracePath, "utf8"))
  : null;
if (solverInputReference &&
    (!solverInputTraceOutput || !Number.isInteger(solverInputTraceEvent) ||
     !Number.isInteger(solverInputTraceSubstep) ||
     !engineDiagnosticEvents.has(solverInputTraceEvent) ||
     process.env.NW_MARBLE_PLAY_TRACE_NEWTON !== "1")) {
  throw new Error("exact solver-input capture requires an output path, integer " +
    "event/substep, that event in NW_MARBLE_PLAY_TRACE_ENGINE_EVENTS, and " +
    "NW_MARBLE_PLAY_TRACE_NEWTON=1");
}

function synchronizeSolverInputFromTrace(model, data, engine, mujoco) {
  data.time = engine.time;
  data.ncon = engine.ncon;
  data.nefc = engine.nefc;
  data.nisland = engine.nisland;
  data.nidof = engine.nidof;
  for (const field of engineDiagnosticFields) {
    const values = engine.arrays[field];
    const target = data[field];
    if (!values || !target || typeof target.set !== "function" ||
        target.length !== values.length) {
      throw new Error(`cannot synchronize diagnostic solver input ${field}`);
    }
    target.set(values);
  }
  model.opt.gravity.set(engine.model.gravity);
  model.opt.timestep = engine.model.timestep;
  model.geom_contype.set(engine.model.geom_contype);
  model.geom_conaffinity.set(engine.model.geom_conaffinity);
  if (model.M_rownnz.some((value, index) =>
      Number(value) !== engine.model.M_rownnz[index]) ||
      model.M_rowadr.some((value, index) =>
        Number(value) !== engine.model.M_rowadr[index]) ||
      model.M_colind.some((value, index) =>
        Number(value) !== engine.model.M_colind[index])) {
    throw new Error("diagnostic solver model sparse layout differs from reference");
  }
  if (engine.ncon && typeof mujoco.marbleSyncSolverContacts !== "function") {
    throw new Error("diagnostic MuJoCo module lacks marbleSyncSolverContacts");
  }
  if (engine.ncon && !mujoco.marbleSyncSolverContacts(data, engine.contacts)) {
    throw new Error("diagnostic MuJoCo rejected solver contact sync");
  }

  const mismatches = [];
  for (const field of engineDiagnosticFields) {
    if (solverOutputFields.has(field)) continue;
    const expected = engine.arrays[field];
    const actual = data[field];
    for (let index = 0; index < expected.length; index++) {
      if (Number(actual[index]) !== expected[index]) {
        mismatches.push({field, index, actual: Number(actual[index]),
          expected: expected[index]});
        if (mismatches.length === 8) break;
      }
    }
    if (mismatches.length === 8) break;
  }
  if (Number(data.time) !== engine.time || Number(data.ncon) !== engine.ncon ||
      Number(data.nefc) !== engine.nefc || Number(data.nisland) !== engine.nisland ||
      Number(data.nidof) !== engine.nidof) {
    mismatches.push({field: "counts", actual: [Number(data.time),
      Number(data.ncon), Number(data.nefc), Number(data.nisland),
      Number(data.nidof)], expected: [engine.time, engine.ncon, engine.nefc,
      engine.nisland, engine.nidof]});
  }
  for (let index = 0; index < engine.ncon; index++) {
    const expected = engine.contacts[index];
    const actual = data.contact.get(index);
    for (const field of ["geom1", "geom2", "dist", "dim", "mu"]) {
      if (Number(actual[field]) !== expected[field]) {
        mismatches.push({field: `contact[${index}].${field}`,
          actual: Number(actual[field]), expected: expected[field]});
      }
    }
    for (const field of ["pos", "frame", "friction"]) {
      const values = Array.from(actual[field], Number);
      if (values.some((value, i) => value !== expected[field][i])) {
        mismatches.push({field: `contact[${index}].${field}`,
          actual: values, expected: expected[field]});
      }
    }
  }
  if (mismatches.length) {
    throw new Error(`diagnostic solver input failed exact sync: ${JSON.stringify(mismatches)}`);
  }
}

function contactPointJacobianDiagnostics(game) {
  const model = game.model;
  const data = game.data;
  const nv = Number(model.nv);
  // Owned WASM buffers do not depend on the current constraint allocation.
  // Never borrow live solver storage or use a JS-only byteOffset as a pointer.
  const jacpBuffer = new game.mujoco.DoubleBuffer(3 * nv);
  let jacrBuffer;
  const diagnostics = {};
  try {
    jacrBuffer = new game.mujoco.DoubleBuffer(3 * nv);
    for (let contactIndex = 0; contactIndex < Number(data.ncon); contactIndex++) {
      const contact = data.contact.get(contactIndex);
      for (let side = 0; side < 2; side++) {
        const geom = Number(side === 0 ? contact.geom1 : contact.geom2);
        if (geom < 0) continue;
        const body = Number(model.geom_bodyid[geom]);
        // Reacquire views after each call: a binding may grow WASM memory,
        // detaching views captured before the call.
        game.mujoco.mj_jac(model, data, jacpBuffer, jacrBuffer, contact.pos, body);
        diagnostics[`contact${contactIndex}_side${side}_jacp`] =
          Array.from(jacpBuffer.GetView(), Number);
        diagnostics[`contact${contactIndex}_side${side}_jacr`] =
          Array.from(jacrBuffer.GetView(), Number);
      }
    }
  } finally {
    jacrBuffer?.delete();
    jacpBuffer.delete();
  }
  return diagnostics;
}

// Flatten the live point-Jacobian operands and separately rounded terms for
// contact bodies. This lets the native/source comparator distinguish input
// drift (point, COM, cdof) from contraction/association in mji_cross and the
// final translational-Jacobian addition.
function contactJacobianTermDiagnostics(model, data) {
  const terms = [];
  for (let contactIndex = 0; contactIndex < Number(data.ncon); contactIndex++) {
    const contact = data.contact.get(contactIndex);
    for (let side = 0; side < 2; side++) {
      const geom = Number(side === 0 ? contact.geom1 : contact.geom2);
      if (geom < 0) continue;
      const body = Number(model.geom_bodyid[geom]);
      const root = Number(model.body_rootid[body]);
      const point = Array.from(contact.pos, Number);
      const com = Array.from(data.subtree_com.subarray(root * 3, root * 3 + 3), Number);
      const offset = point.map((value, axis) => value - com[axis]);
      let dof = Number(model.body_dofadr[body]) +
        Number(model.body_dofnum[body]) - 1;
      while (dof >= 0) {
        const spatial = Array.from(
          data.cdof.subarray(dof * 6, dof * 6 + 6), Number);
        const products = [
          [spatial[1] * offset[2], spatial[2] * offset[1]],
          [spatial[2] * offset[0], spatial[0] * offset[2]],
          [spatial[0] * offset[1], spatial[1] * offset[0]],
        ];
        const translation = spatial.slice(3, 6);
        terms.push(contactIndex, side, body, dof, ...point, ...com,
          ...offset, ...spatial);
        for (let component = 0; component < 3; component++) {
          const cross = products[component][0] - products[component][1];
          terms.push(...products[component], translation[component], cross,
            translation[component] + cross);
        }
        dof = Number(model.dof_parentid[dof]);
      }
    }
  }
  return terms;
}

// Record the exact intermediate vectors used by mj_comVel for root free
// joints. Their parent spatial velocity is zero and the first three free
// joint DOFs are the world translation basis, so this reconstruction is exact
// for the Marble model (unlike subtracting angular velocity from final cvel).
function freeJointCrossMotionDiagnostics(model, data) {
  const output = [];
  for (let body = 1; body < model.body_parentid.length; body++) {
    if (Number(model.body_parentid[body]) !== 0 ||
        Number(model.body_dofnum[body]) !== 6) continue;
    const bda = Number(model.body_dofadr[body]);
    const joint = Number(model.dof_jntid[bda]);
    if (Number(model.jnt_type[joint]) !== 0) continue;

    const vel = [0, 0, 0, 0, 0, 0];
    for (let dof = 0; dof < 3; dof++) {
      const qvel = Number(data.qvel[bda + dof]);
      for (let component = 0; component < 6; component++) {
        vel[component] += Number(data.cdof[(bda + dof) * 6 + component]) * qvel;
      }
    }
    for (let dof = 3; dof < 6; dof++) {
      const index = bda + dof;
      output.push(body, index, ...vel);
      for (let component = 0; component < 6; component++) {
        output.push(Number(data.cdof[index * 6 + component]));
      }
      for (let component = 0; component < 6; component++) {
        output.push(Number(data.cdof_dot[index * 6 + component]));
      }
    }
  }
  return output;
}

function physicsSnapshot(game, eventIndex = -1) {
  const snapshot = {
    marbles: game.marbles.map((marble) => ({
      values: [marble.x, marble.y, marble.z, marble.vx, marble.vy,
        marble.vz, marble.qw, marble.qx, marble.qy, marble.qz,
        marble.wx, marble.wy, marble.wz],
      state: marble.state,
      over: marble.over === null ? null : game.board.holes.indexOf(marble.over),
    })),
    roll: game.roll,
    pitch: game.pitch,
    elapsed: game.elapsed,
    struck: game.struckThisStep,
    cupped: game.cuppedThisStep,
    lostThisStep: game.lostThisStep,
    home: game.home,
    lost: game.lost,
    nudgeDue: game.nudgeDue,
  };
  if (process.env.NW_MARBLE_PLAY_TRACE_CONTACTS === "1" && game.data) {
    snapshot.qaccWarmstart = Array.from(game.data.qacc_warmstart, Number);
    snapshot.contacts = Array.from({ length: Number(game.data.ncon) }, (_, index) => {
      const contact = game.data.contact.get(index);
      return {
        geom1: Number(contact.geom1),
        geom2: Number(contact.geom2),
        dist: Number(contact.dist),
        pos: Array.from(contact.pos, Number),
      };
    });
  }
  if (engineDiagnosticEvents.has(eventIndex) && game.data) {
    const islandCount = game.data.solver_niter.length;
    const solverCapacity = islandCount
      ? Math.floor(game.data.solver.size() / islandCount) : 0;
    const solverStats = [];
    for (let island = 0; island < islandCount; island++) {
      const iterations = Math.min(solverCapacity,
        Number(game.data.solver_niter[island]));
      for (let iteration = 0; iteration < iterations; iteration++) {
        const stat = game.data.solver.get(island * solverCapacity + iteration);
        solverStats.push(island, iteration,
          Number(stat.improvement), Number(stat.gradient),
          Number(stat.lineslope), Number(stat.nactive),
          Number(stat.nchange), Number(stat.neval), Number(stat.nupdate));
      }
    }
    snapshot.engine = {
      time: Number(game.data.time),
      ncon: Number(game.data.ncon),
      nefc: Number(game.data.nefc),
      nisland: Number(game.data.nisland),
      nidof: Number(game.data.nidof),
      flags: {
        flg_energypos: Number(game.data.flg_energypos),
        flg_energyvel: Number(game.data.flg_energyvel),
        flg_subtreevel: Number(game.data.flg_subtreevel),
        flg_rnepost: Number(game.data.flg_rnepost),
      },
      contacts: Array.from({ length: Number(game.data.ncon) }, (_, index) => {
        const contact = game.data.contact.get(index);
        return {
          geom1: Number(contact.geom1),
          geom2: Number(contact.geom2),
          dist: Number(contact.dist),
          pos: Array.from(contact.pos, Number),
          frame: Array.from(contact.frame, Number),
          dim: Number(contact.dim),
          mu: Number(contact.mu),
          friction: Array.from(contact.friction, Number),
        };
      }),
      arrays: {
        ...Object.fromEntries(engineDiagnosticFields.map((field) => [
          field, Array.from(game.data[field] ?? [], Number),
        ])),
        ...contactPointJacobianDiagnostics(game),
        contact_jacobian_terms: contactJacobianTermDiagnostics(
          game.model, game.data),
        free_joint_cross_motion: freeJointCrossMotionDiagnostics(
          game.model, game.data),
        solver_stats: solverStats,
      },
      model: {
        gravity: Array.from(game.model.opt.gravity, Number),
        timestep: Number(game.model.opt.timestep),
        disableflags: Number(game.model.opt.disableflags),
        solver: Number(game.model.opt.solver),
        options: {
          integrator: Number(game.model.opt.integrator),
          cone: Number(game.model.opt.cone),
          jacobian: Number(game.model.opt.jacobian),
          solver: Number(game.model.opt.solver),
          iterations: Number(game.model.opt.iterations),
          ls_iterations: Number(game.model.opt.ls_iterations),
          noslip_iterations: Number(game.model.opt.noslip_iterations),
          tolerance: Number(game.model.opt.tolerance),
          ls_tolerance: Number(game.model.opt.ls_tolerance),
          noslip_tolerance: Number(game.model.opt.noslip_tolerance),
          impratio: Number(game.model.opt.impratio),
          disableflags: Number(game.model.opt.disableflags),
          enableflags: Number(game.model.opt.enableflags),
          density: Number(game.model.opt.density),
          viscosity: Number(game.model.opt.viscosity),
        },
        // MuJoCo 3.12 selects sparse constraints explicitly, or in AUTO mode
        // only when nv >= 60. Record the resolved mode so inactive sparse
        // storage is not mistaken for initialized diagnostic output.
        sparse_jacobian: Number(game.model.opt.jacobian) === 1 ||
          (Number(game.model.opt.jacobian) === 2 && Number(game.model.nv) >= 60),
        M_rownnz: Array.from(game.model.M_rownnz, Number),
        M_rowadr: Array.from(game.model.M_rowadr, Number),
        M_colind: Array.from(game.model.M_colind, Number),
        geom_bodyid: Array.from(game.model.geom_bodyid, Number),
        body_rootid: Array.from(game.model.body_rootid, Number),
        body_parentid: Array.from(game.model.body_parentid, Number),
        body_dofadr: Array.from(game.model.body_dofadr, Number),
        body_dofnum: Array.from(game.model.body_dofnum, Number),
        dof_parentid: Array.from(game.model.dof_parentid, Number),
        body_pos: Array.from(game.model.body_pos, Number),
        body_quat: Array.from(game.model.body_quat, Number),
        body_ipos: Array.from(game.model.body_ipos, Number),
        body_iquat: Array.from(game.model.body_iquat, Number),
        body_inertia: Array.from(game.model.body_inertia, Number),
        body_mass: Array.from(game.model.body_mass, Number),
        geom_pos: Array.from(game.model.geom_pos, Number),
        geom_quat: Array.from(game.model.geom_quat, Number),
        geom_size: Array.from(game.model.geom_size, Number),
        geom_friction: Array.from(game.model.geom_friction, Number),
        geom_condim: Array.from(game.model.geom_condim, Number),
        geom_contype: Array.from(game.model.geom_contype, Number),
        geom_conaffinity: Array.from(game.model.geom_conaffinity, Number),
        jnt_axis: Array.from(game.model.jnt_axis, Number),
        jnt_pos: Array.from(game.model.jnt_pos, Number),
        jnt_qposadr: Array.from(game.model.jnt_qposadr, Number),
        jnt_dofadr: Array.from(game.model.jnt_dofadr, Number),
        jnt_type: Array.from(game.model.jnt_type, Number),
        dof_jntid: Array.from(game.model.dof_jntid, Number),
      },
    };
  }
  return snapshot;
}

function findCellRoute(board, fromCell = null) {
  const originX = (board.width - board.cols * board.cell) / 2;
  const originY = (board.depth - board.rows * board.cell) / 2;
  const tolerance = board.thickness * 1.01 + 1e-8;
  const cellOf = (point) => [
    Math.min(board.cols - 1, Math.max(0,
      Math.floor((point.x - originX) / board.cell))),
    Math.min(board.rows - 1, Math.max(0,
      Math.floor((point.y - originY) / board.cell))),
  ];
  const start = fromCell ?? cellOf(board.starts[0]);
  const home = cellOf(board.home);
  const key = (column, row) => `${column},${row}`;
  const blocked = (column, row, nextColumn, nextRow) => {
    if (nextColumn !== column) {
      const x = originX + (Math.min(column, nextColumn) + 1) * board.cell;
      const y = originY + (row + 0.5) * board.cell;
      return board.walls.some((wall) => wall.x0 <= x + tolerance &&
        wall.x1 >= x - tolerance && wall.y0 <= y + tolerance &&
        wall.y1 >= y - tolerance);
    }
    const y = originY + (Math.min(row, nextRow) + 1) * board.cell;
    const x = originX + (column + 0.5) * board.cell;
    return board.walls.some((wall) => wall.y0 <= y + tolerance &&
      wall.y1 >= y - tolerance && wall.x0 <= x + tolerance &&
      wall.x1 >= x - tolerance);
  };
  const queue = [start];
  const previous = new Map([[key(...start), null]]);
  const direction = new Map();
  for (let index = 0; index < queue.length; index++) {
    const [column, row] = queue[index];
    for (const [dc, dr, name] of [
      [1, 0, "E"], [-1, 0, "W"], [0, 1, "N"], [0, -1, "S"],
    ]) {
      const next = [column + dc, row + dr];
      const nextKey = key(...next);
      if (next[0] < 0 || next[0] >= board.cols ||
          next[1] < 0 || next[1] >= board.rows || previous.has(nextKey) ||
          blocked(column, row, ...next)) continue;
      previous.set(nextKey, [column, row]);
      direction.set(nextKey, name);
      queue.push(next);
    }
  }
  let current = home;
  const cells = [];
  let route = "";
  while (previous.get(key(...current)) !== null) {
    cells.unshift(current);
    route = direction.get(key(...current)) + route;
    current = previous.get(key(...current));
  }
  assert.deepEqual(current, start, "generated wall strips have no start/home route");
  cells.unshift(start);
  const routeCells = cells.map(([column, row]) => [column, row]);
  return {
    route,
    cells: cells.map(([column, row]) => ({
      x: originX + (column + 0.5) * board.cell,
      y: originY + (row + 0.5) * board.cell,
    })),
    cellOf,
    routeIndexOf: (cell) => routeCells.findIndex(([column, row]) =>
      column === cell[0] && row === cell[1]),
    homeCell: cellOf(board.home),
  };
}

let timestamp = 0n;
let sequence = 0n;
function dispatch(handle, kind, code, value = 0n, aux = 0n) {
  timestamp += 1n;
  sequence += 1n;
  return exports.nw_api_v1_dispatch(
    handle, kind, timestamp, sequence, code, BigInt(value), 0n,
    0n, 0n, 0n, BigInt(aux));
}

function advance(handle, elapsedMs) {
  timestamp += BigInt(elapsedMs);
  sequence += 1n;
  return exports.nw_api_v1_advance(
    handle, timestamp, BigInt(elapsedMs), sequence);
}

// These run seeds select board seeds from the same persistent CPython stream
// used by the browser. The route is reconstructed from each resulting board;
// no expected board positions are hard-coded in the test. The expected
// outcome is retained as a small oracle for the deterministic held-input
// driver: it makes a change in hole-edge ordering or key direction fail at
// the result boundary rather than merely shortening the route.
const selectedCases = [
  { rung: 1, runSeed: 17, expected: "won" },
  { rung: 1, runSeed: 1073741823, expected: "won" },
  { rung: 2, runSeed: 1, expected: "won" },
  { rung: 2, runSeed: 17, expected: "lost" },
  { rung: 2, runSeed: 1073741823, expected: "lost" },
  { rung: 3, runSeed: 0, expected: "lost" },
  { rung: 3, runSeed: 1, expected: "lost" },
  { rung: 3, runSeed: 17, expected: "lost" },
  { rung: 3, runSeed: 314159, expected: "lost" },
  { rung: 3, runSeed: 1073741823, expected: "lost" },
  { rung: 4, runSeed: 0, expected: "lost" },
  { rung: 4, runSeed: 1, expected: "lost" },
  { rung: 4, runSeed: 17, expected: "lost" },
  { rung: 4, runSeed: 314159, expected: "lost" },
  { rung: 4, runSeed: 1073741823, expected: "lost" },
  { rung: 6, runSeed: 1, expected: "lost" },
  { rung: 6, runSeed: 17, expected: "lost" },
  { rung: 6, runSeed: 314159, expected: "lost" },
  { rung: 8, runSeed: 0, expected: "lost" },
  { rung: 8, runSeed: 1, expected: "lost" },
  { rung: 8, runSeed: 314159, expected: "lost" },
  { rung: 8, runSeed: 1073741823, expected: "lost" },
  { rung: 10, runSeed: 0, expected: "lost" },
  { rung: 10, runSeed: 1, expected: "lost" },
  { rung: 10, runSeed: 17, expected: "lost" },
  { rung: 10, runSeed: 314159, expected: "lost" },
  { rung: 10, runSeed: 1073741823, expected: "lost" },
  { rung: 12, runSeed: 1, expected: "lost" },
  { rung: 12, runSeed: 17, expected: "lost" },
  { rung: 12, runSeed: 314159, expected: "lost" },
  { rung: 12, runSeed: 1073741823, expected: "lost" },
  { rung: 14, runSeed: 0, expected: "lost" },
  { rung: 14, runSeed: 1, expected: "lost" },
  { rung: 14, runSeed: 17, expected: "lost" },
  { rung: 14, runSeed: 314159, expected: "lost" },
  { rung: 14, runSeed: 1073741823, expected: "lost" },
];
const runSeeds = [0, 1, 17, 314159, 1073741823];
const casesByBoard = new Map(selectedCases.map((testCase) => [
  `${testCase.rung}:${testCase.runSeed}`,
  testCase,
]));
// The lower/single-marble rungs are suitable for bounded feedback steering.
// Add the remaining certified seeds so this held-play matrix covers every
// single-marble transport board, while preserving all existing oracle cases.
for (const rung of [1, 2, 3, 4, 6, 8, 12]) {
  for (const runSeed of runSeeds) {
    const key = `${rung}:${runSeed}`;
    if (!casesByBoard.has(key)) {
      casesByBoard.set(key, { rung, runSeed, expected: null });
    }
  }
}
for (const rung of [5, 7, 9, 11, 13, 15, 16]) {
  for (const runSeed of runSeeds) {
    const key = `${rung}:${runSeed}`;
    if (!casesByBoard.has(key)) {
      casesByBoard.set(key, { rung, runSeed, expected: null });
    }
  }
}
const cases = [...casesByBoard.values()];
const probeCase = process.env.NW_MARBLE_PLAY_CASE;
if (probeCase) {
  const selected = casesByBoard.get(probeCase) ?? (() => {
    const [rung, runSeed] = probeCase.split(":").map(Number);
    return { rung, runSeed, expected: null };
  })();
  assert.ok(Number.isInteger(selected.rung) && Number.isInteger(selected.runSeed),
    `invalid NW_MARBLE_PLAY_CASE ${probeCase}`);
  cases.splice(0, cases.length, selected);
}
const tracePath = process.env.NW_MARBLE_PLAY_TRACE_PATH;
const traceDirectory = process.env.NW_MARBLE_PLAY_TRACE_DIR;
const inputTracePath = process.env.NW_MARBLE_PLAY_INPUT_TRACE_PATH;
const inputTrace = inputTracePath
  ? JSON.parse(fs.readFileSync(inputTracePath, "utf8")) : null;
const inputTraceIdentity = inputTracePath ? {
  path: resolve(inputTracePath),
  sha256: sha256(fs.readFileSync(inputTracePath)),
  events: inputTrace.events?.length ?? 0,
} : null;
if (inputTracePath) {
  assert.ok(tracePath,
    "input-trace replay must write a fresh current-runtime trace");
  assert.equal(traceDirectory, undefined,
    "input-trace replay cannot be combined with a trace batch");
  assert.ok(probeCase,
    "input-trace replay requires one explicit NW_MARBLE_PLAY_CASE");
  assert.equal(cases.length, 1,
    "input-trace replay requires exactly one selected case");
  assert.equal(inputTrace.version, 1);
  assert.equal(inputTrace.rung, cases[0].rung);
  assert.equal(inputTrace.runSeed, cases[0].runSeed);
  assert.equal(inputTrace.timeLimitMs, 120000);
  assert.ok(Array.isArray(inputTrace.events) && inputTrace.events.length > 0,
    "input trace must contain ordered events");
  for (const [index, event] of inputTrace.events.entries()) {
    if (event.kind === "frame") {
      assert.ok(Number.isFinite(event.dt) && event.dt >= 0,
        `invalid frame duration in input trace event ${index}`);
      assert.ok(Array.isArray(event.held) && event.held.every((name) =>
        Object.hasOwn(KEY, name)),
      `invalid held directions in input trace event ${index}`);
    } else {
      assert.equal(event.kind, "level",
        `unsupported input trace event ${index}: ${event.kind}`);
    }
  }
}
const traceBatchIndexValue = process.env.NW_MARBLE_PLAY_TRACE_BATCH_INDEX;
const traceBatchCountValue = process.env.NW_MARBLE_PLAY_TRACE_BATCH_COUNT;
assert.equal(traceBatchIndexValue === undefined,
  traceBatchCountValue === undefined,
  "trace batch index and count must be provided together");
if (traceBatchIndexValue !== undefined) {
  assert.ok(traceDirectory,
    "bounded trace batches require NW_MARBLE_PLAY_TRACE_DIR");
  assert.equal(tracePath, undefined,
    "bounded trace batches cannot be combined with a single trace path");
  assert.equal(probeCase, undefined,
    "bounded trace batches cannot be combined with NW_MARBLE_PLAY_CASE");
  assert.match(traceBatchIndexValue, /^\d+$/,
    "trace batch index must be a nonnegative integer");
  assert.match(traceBatchCountValue, /^\d+$/,
    "trace batch count must be a positive integer");
  const traceBatchIndex = Number(traceBatchIndexValue);
  const traceBatchCount = Number(traceBatchCountValue);
  assert.ok(Number.isSafeInteger(traceBatchIndex) &&
    Number.isSafeInteger(traceBatchCount) && traceBatchCount > 0 &&
    traceBatchCount <= cases.length && traceBatchIndex < traceBatchCount,
  `invalid trace batch ${traceBatchIndexValue}/${traceBatchCountValue} ` +
    `for ${cases.length} cases`);
  const batchStart = Math.floor(traceBatchIndex * cases.length / traceBatchCount);
  const batchEnd = Math.floor((traceBatchIndex + 1) * cases.length / traceBatchCount);
  cases.splice(0, cases.length, ...cases.slice(batchStart, batchEnd));
  assert.ok(cases.length > 0, "trace batch must contain at least one case");
}
const resourceStats = globalThis.__NW_MARBLE_MUJOCO_RESOURCE_STATS__;
assert.equal(typeof resourceStats, "function");
const resourceBaseline = resourceStats();
const outcomeCounts = { won: 0, physicalLoss: 0, timeout: 0 };
if (tracePath) {
  assert.equal(cases.length, 1,
    "source parity trace mode requires exactly one NW_MARBLE_PLAY_CASE");
}

for (const testCase of cases) {
  timestamp = 0n;
  sequence = 0n;
  const handle = exports.nw_api_v1_create(
    TASK_MARBLE, 1n, BigInt(testCase.rung), 1n, 0n, 2600n,
    120000n, 1n, BigInt(testCase.runSeed));
  assert.ok(handle > 0n);
  let game = null;
  let destroyed = false;
  try {
    assert.equal(dispatch(handle, EVENT.action, ACTION.start), STATUS.accepted);
    let state = readState(handle);
    assert.equal(state[INFO.phase], PHASE.running);
    const boardSeed = Number(state[INFO.seed]);
    const board = boardForState(state);
    if (process.env.NW_MARBLE_PLAY_DEBUG === "1") {
      console.log("generated play probe board", JSON.stringify({
        rung: testCase.rung,
        runSeed: testCase.runSeed,
        boardSeed: Number(state[INFO.seed]),
        width: board.width,
        depth: board.depth,
        cell: board.cell,
        starts: board.starts,
        home: board.home,
      }));
    }
    let routePlan = findCellRoute(board);
    let route = routePlan.route;
    game = new Game(board);
    if (solverInputReference &&
        typeof game.mujoco.marbleNewtonTrace !== "function") {
      throw new Error("exact solver-input capture needs an instrumented MuJoCo module");
    }
    const replayEvents = tracePath || traceDirectory ? [] : null;
    if (replayEvents) {
      let activeEngineSubsteps = null;
      let activeSubstepStates = null;
      let activeStep1Substeps = null;
      let activeStep1Inputs = null;
      let activeStep1Phases = null;
      let activeStep2Phases = null;
      let activeRneTraces = null;
      let activeRneAwakeStates = null;
      let activeNewtonTraces = null;
      let activeDiagnosticEvent = -1;
      const substep = game.substep.bind(game);
      if (process.env.NW_MARBLE_PLAY_TRACE_SPLIT_STEP === "1") {
        const mujoco = game.mujoco;
        const originalMjStep = mujoco.mj_step.bind(mujoco);
        mujoco.mj_step = (model, data) => {
          if (!activeStep1Substeps) {
            originalMjStep(model, data);
            return;
          }
          if (activeStep1Inputs) {
            activeStep1Inputs.push(physicsSnapshot(game, activeDiagnosticEvent).engine);
          }
          if (activeStep1Phases) {
            const phases = [];
            activeStep1Phases.push(phases);
            const capturePhase = (phase, rneProjectionTrace = null) => {
              const captured = {
                phase,
                engine: physicsSnapshot(game, activeDiagnosticEvent).engine,
              };
              if (phase === "checkAcc" &&
                  process.env.NW_MARBLE_CAPTURE_FREE_SOLVE === "1" &&
                  typeof mujoco.marbleFreeJointSolveProbe === "function") {
                captured.freeJointSolveProbe = Array.from(
                  mujoco.marbleFreeJointSolveProbe(model, data), Number);
              }
              if (rneProjectionTrace) {
                captured.rneProjectionTrace = rneProjectionTrace;
              }
              phases.push(captured);
            };
            mujoco.mj_checkPos(model, data);
            capturePhase("checkPos");
            mujoco.mj_checkVel(model, data);
            capturePhase("checkVel");
            // Read these adjacent forward-position kernels separately. The
            // following complete fwdPosition call restores the exact official
            // step1 sequence before the simulation continues.
            mujoco.mj_kinematics(model, data);
            capturePhase("kinematics");
            mujoco.mj_comPos(model, data);
            capturePhase("comPos");
            mujoco.mj_fwdPosition(model, data);
            capturePhase("fwdPosition");
            mujoco.mj_sensorPos(model, data);
            capturePhase("sensorPos");
            const probeData = new mujoco.MjData(model, data);
            const liveData = game.data;
            game.data = probeData;
            try {
              capturePhase("probe_input");
              mujoco.mj_comVel(model, probeData);
              capturePhase("probe_comVel");
              mujoco.mj_passive(model, probeData);
              capturePhase("probe_passive");
              mujoco.mj_referenceConstraint(model, probeData);
              capturePhase("probe_referenceConstraint");
              const captureRneTrace = typeof mujoco.marbleRneTrace === "function"
                ? mujoco.marbleRneTrace
                : mujoco.marbleRneProjectionTrace;
              if (activeRneTraces && typeof captureRneTrace === "function") {
                activeRneTraces.push(Array.from(
                  captureRneTrace(model, probeData), Number));
                activeRneAwakeStates.push(
                  typeof mujoco.marbleAwakeState === "function"
                    ? mujoco.marbleAwakeState(model, probeData) : null);
              }
              mujoco.mj_rne(model, probeData, 0, probeData.qfrc_bias);
              const rneProjectionTrace =
                typeof mujoco.marbleRneProjectionTrace === "function"
                  ? Array.from(mujoco.marbleRneProjectionTrace(
                    model, probeData), Number)
                  : null;
              capturePhase("probe_rneBias", rneProjectionTrace);
              probeData.qacc.fill(0);
              mujoco.mj_rnePostConstraint(model, probeData);
              capturePhase("probe_rnePostConstraint_zeroacc");
            } finally {
              game.data = liveData;
              probeData.delete();
            }
            mujoco.mj_fwdVelocity(model, data);
            capturePhase("fwdVelocity");
            mujoco.mj_sensorVel(model, data);
            capturePhase("sensorVel");
          } else {
          mujoco.mj_step1(model, data);
          }
          if (activeStep1Substeps) {
            activeStep1Substeps.push(
              physicsSnapshot(game, activeDiagnosticEvent).engine);
          }
          if (activeStep2Phases) {
            const phases = [];
            activeStep2Phases.push(phases);
            const capturePhase = (phase) => {
              const captured = {
                phase,
                engine: physicsSnapshot(game, activeDiagnosticEvent).engine,
              };
              if (process.env.NW_MARBLE_PLAY_TRACE_INTEGRATOR === "1" &&
                  ["checkAcc", "implicit"].includes(phase)) {
                captured.engine.integratorReadSet = captureIntegrator(model, data, phase);
              }
              if (phase === "checkAcc" &&
                  process.env.NW_MARBLE_CAPTURE_FREE_SOLVE === "1" &&
                  typeof mujoco.marbleFreeJointSolveProbe === "function") {
                captured.bodyXmat = Array.from(data.xmat, Number);
                captured.jointBodyIds = Array.from(model.jnt_bodyid, Number);
                captured.freeJointSolveProbe = Array.from(
                  mujoco.marbleFreeJointSolveProbe(model, data), Number);
                if (typeof mujoco.marbleFreeJointAdvanceProbe === "function") {
                  captured.freeJointAdvanceProbe = Array.from(
                    mujoco.marbleFreeJointAdvanceProbe(model, data), Number);
                }
                if (typeof mujoco.marbleFreeJointDerivativeProbe === "function") {
                  captured.freeJointDerivativeProbe = Array.from(
                    mujoco.marbleFreeJointDerivativeProbe(model, data), Number);
                }
                if (typeof mujoco.marbleFreeBiasIntermediateProbe === "function") {
                  captured.freeBiasIntermediateProbe = Array.from(
                    mujoco.marbleFreeBiasIntermediateProbe(model, data), Number);
                }
              }
              phases.push(captured);
            };
            mujoco.mj_fwdActuation(model, data);
            capturePhase("fwdActuation");
            mujoco.mj_fwdAcceleration(model, data);
            capturePhase("fwdAcceleration");
            const solverInputSubstep = activeStep2Phases.length - 1;
            const referenceSolverEvent = solverInputReference?.events?.[
              activeDiagnosticEvent];
            const synchronizeThisSolverCall = Boolean(
              referenceSolverEvent &&
              activeDiagnosticEvent === solverInputTraceEvent &&
              solverInputSubstep === solverInputTraceSubstep);
            if (synchronizeThisSolverCall) {
              const phases = referenceSolverEvent.engineStep2Phases?.[
                solverInputSubstep];
              if (phases?.[1]?.phase !== "fwdAcceleration" ||
                  phases?.[2]?.phase !== "fwdConstraint") {
                throw new Error("reference trace lacks the expected solver phases");
              }
              synchronizeSolverInputFromTrace(model, data, phases[1].engine,
                mujoco);
            }
            const useCleanNoSlipTrace =
              process.env.NW_MARBLE_CAPTURE_NOSLIP_RESIDUAL === "1" &&
              typeof mujoco.marbleNoSlipResidualTrace === "function";
            if (activeNewtonTraces &&
                (typeof mujoco.marbleNewtonTrace === "function" ||
                 useCleanNoSlipTrace)) {
              // marbleNewtonTrace runs exactly one instrumented
              // mj_fwdConstraint call and returns its traces. Calling
              // mj_fwdConstraint separately here would advance solver state
              // twice on WASM while the native comparator advances it once.
              const trace = useCleanNoSlipTrace
                ? { noSlipResidualTrace:
                    mujoco.marbleNoSlipResidualTrace(model, data) }
                : mujoco.marbleNewtonTrace(model, data);
              assert.equal(Number(trace.coneHessianUpdateOverflow ?? 0), 0,
                "cone-Hessian recorder overflowed or rejected a record");
              assert.equal(Number(trace.constraintIterationTraceOverflow ?? 0), 0,
                "constraint-iteration recorder overflowed");
              if (trace.prepareTraceSchema !== undefined) {
                assert.equal(trace.prepareTraceSchema, 1, "unsupported preparation schema");
                assert.equal(trace.prepareTraceOverflow, false, "preparation recorder overflowed");
                assert.equal(trace.prepareTraceInvalid, false, "preparation recorder copied invalid fields");
              }
              if (trace.evalTraceSchema !== undefined) {
                assert.equal(trace.evalTraceSchema, 1, "unsupported evaluation schema");
                assert.equal(trace.evalTraceOverflow, false, "evaluation recorder overflowed");
                assert.equal(trace.evalTraceInvalid, false, "evaluation recorder copied invalid fields");
                assert.equal(trace.prepareTraceSchema, 1, "evaluation needs associated preparations");
              }
              if (trace.qcqpTraceSchema !== undefined) {
                assert.equal(trace.qcqpTraceSchema, 1, "unsupported QCQP schema");
                assert.equal(trace.qcqpTraceOverflow, false, "QCQP recorder overflowed");
                assert.equal(trace.qcqpTraceInvalid, false, "QCQP recorder copied invalid fields");
              }
              if (trace.qcqpKernelSchema !== undefined) {
                assert.equal(trace.qcqpKernelSchema, 1, "unsupported QCQP kernel schema");
                assert.equal(trace.qcqpKernelOverflow, false, "QCQP kernel recorder overflowed");
                assert.equal(trace.qcqpKernelInvalid, false, "QCQP kernel recorder copied invalid fields");
              }
              if (trace.gaussSchema !== undefined) {
                assert.equal(trace.gaussSchema, 1, "unsupported Gauss schema");
                assert.equal(trace.gaussOverflow, false, "Gauss recorder overflowed");
                assert.equal(trace.gaussInvalid, false, "Gauss recorder copied invalid operands");
              }
              if (trace.costChangeSchema !== undefined) {
                assert.equal(trace.costChangeSchema, 1, "unsupported costChange schema");
                assert.equal(trace.costChangeOverflow, false, "costChange recorder overflowed");
                assert.equal(trace.costChangeInvalid, false, "costChange recorder copied invalid operands");
              }
              const noSlipIterationTrace = Array.from(
                trace.noSlipTrace ?? [], Number);
              const noSlipContactTrace = Array.from(
                trace.noSlipContactTrace ?? [], Number);
              const residualInputStates = Array.from(
                trace.residualInputStates ?? [], (state) => ({
                  island: Number(state.island),
                  islandNefc: Number(state.islandNefc),
                  efclist: Array.from(state.efclist ?? [], Number),
                  nefc: Number(state.nefc),
                  b: Array.from(state.b ?? [], Number),
                  R: Array.from(state.R ?? [], Number),
                  force: Array.from(state.force ?? [], Number),
                  AR: Array.from(state.AR ?? [], Number),
                  arAvailable: Boolean(state.arAvailable),
                }));
              activeNewtonTraces.push({
                records: Number(trace.records),
                traceKeys: Object.keys(trace).sort(),
                modelDisableFlags: Number(trace.modelDisableFlags),
                modelSolver: Number(trace.modelSolver),
                dataConstraintCount: Number(trace.dataConstraintCount),
                constraintUpdateCaptureSize: Number(
                  trace.constraintUpdateCaptureSize),
                values: Array.from(trace.values ?? [], Number),
                jarefTrace: Array.from(trace.jarefTrace ?? [], Number),
                jvTrace: Array.from(trace.jvTrace ?? [], Number),
                jarefUpdateTrace: Array.from(
                  trace.jarefUpdateTrace ?? [], Number),
                sparseInput: Array.from(trace.sparseInput ?? [], Number),
                constraintInput: Array.from(trace.constraintInput ?? [], Number),
                cholSolveInput: Array.from(trace.cholSolveInput ?? [], Number),
                hessianTrace: Array.from(trace.hessianTrace ?? [], Number),
                coneTrace: Array.from(trace.coneTrace ?? [], Number),
                denseSolveStages: Array.from(trace.denseSolveStages ?? [], Number),
                constraintUpdateTrace: Array.from(
                  trace.constraintUpdateTrace ?? [], Number),
                coneHessianUpdateTrace: Array.from(
                  trace.coneHessianUpdateTrace ?? [], Number),
                coneHessianUpdateSchema: trace.coneHessianUpdateSchema ?? null,
                coneHessianUpdateCalls: Number(trace.coneHessianUpdateCalls ?? 0),
                coneHessianUpdateOverflow: Boolean(trace.coneHessianUpdateOverflow),
                constraintIterationTrace: Array.from(
                  trace.constraintIterationTrace ?? [], Number),
                constraintIterationTraceSchema: Number(
                  trace.constraintIterationTraceSchema ?? 1),
                prepareTrace: Array.from(trace.prepareTrace ?? [], Number),
                prepareTraceSchema: trace.prepareTraceSchema ?? null,
                prepareTraceCalls: trace.prepareTraceCalls ?? null,
                prepareTraceOverflow: trace.prepareTraceOverflow ?? null,
                prepareTraceInvalid: trace.prepareTraceInvalid ?? null,
                evalTrace: Array.from(trace.evalTrace ?? [], Number),
                evalTraceSchema: trace.evalTraceSchema ?? null,
                evalTraceCalls: trace.evalTraceCalls ?? null,
                evalTraceOverflow: trace.evalTraceOverflow ?? null,
                evalTraceInvalid: trace.evalTraceInvalid ?? null,
                qcqpTrace: Array.from(trace.qcqpTrace ?? [], Number),
                qcqpTraceSchema: trace.qcqpTraceSchema ?? null,
                qcqpTraceCalls: trace.qcqpTraceCalls ?? null,
                qcqpTraceOverflow: trace.qcqpTraceOverflow ?? null,
                qcqpTraceInvalid: trace.qcqpTraceInvalid ?? null,
                qcqpKernelTrace: Array.from(trace.qcqpKernelTrace ?? [], Number),
                qcqpKernelSchema: trace.qcqpKernelSchema ?? null,
                qcqpKernelCalls: trace.qcqpKernelCalls ?? null,
                qcqpKernelOverflow: trace.qcqpKernelOverflow ?? null,
                qcqpKernelInvalid: trace.qcqpKernelInvalid ?? null,
                gaussTrace: Array.from(trace.gaussTrace ?? [], Number),
                gaussSchema: trace.gaussSchema ?? null,
                gaussCalls: trace.gaussCalls ?? null,
                gaussOverflow: trace.gaussOverflow ?? null,
                gaussInvalid: trace.gaussInvalid ?? null,
                costChangeTrace: Array.from(trace.costChangeTrace ?? [], Number),
                costChangeSchema: trace.costChangeSchema ?? null,
                costChangeCalls: trace.costChangeCalls ?? null,
                costChangeOverflow: trace.costChangeOverflow ?? null,
                costChangeInvalid: trace.costChangeInvalid ?? null,
                constraintIterationTraceOverflow:
                  trace.constraintIterationTraceOverflow === undefined
                    ? null : Boolean(trace.constraintIterationTraceOverflow),
                constraintStateTrace: Array.from(
                  trace.constraintStateTrace ?? [], Number),
                noSlipTrace: noSlipIterationTrace,
                noSlipStepTrace: Array.from(
                  trace.noSlipStepTrace ?? [], Number),
                noSlipContactTrace,
                noSlipResidualTrace: Array.from(
                  trace.noSlipResidualTrace ?? [], Number),
                noSlipCostChangeProbe: noSlipCostChangeProbes(
                  mujoco, noSlipContactTrace),
                noSlipIteration1DotProbe:
                  process.env.NW_MARBLE_CAPTURE_NOSLIP_DOT === "1"
                    ? noSlipIteration1DotProbes(
                      mujoco, residualInputStates, noSlipIterationTrace,
                      noSlipContactTrace)
                    : [],
                residualInputState: {
                  nefc: Number(trace.residualInputState?.nefc ?? 0),
                  b: Array.from(trace.residualInputState?.b ?? [], Number),
                  R: Array.from(trace.residualInputState?.R ?? [], Number),
                  force: Array.from(trace.residualInputState?.force ?? [], Number),
                  AR: Array.from(trace.residualInputState?.AR ?? [], Number),
                  arAvailable: Boolean(
                    trace.residualInputState?.arAvailable),
                },
                residualInputStates,
              });
              if (synchronizeThisSolverCall) {
                const actual = physicsSnapshot(
                  game, activeDiagnosticEvent).engine;
                const expected = referenceSolverEvent.engineStep2Phases[
                  solverInputSubstep][2].engine;
                const outputDifferences = {};
                for (const field of solverOutputFields) {
                  const left = actual.arrays[field] ?? [];
                  const right = expected.arrays[field] ?? [];
                  const differing = [];
                  for (let index = 0; index < Math.min(left.length, right.length);
                       index++) {
                    if (left[index] !== right[index]) differing.push(index);
                  }
                  if (left.length !== right.length || differing.length) {
                    outputDifferences[field] = {
                      actualLength: left.length,
                      expectedLength: right.length,
                      differentCount: differing.length +
                        Math.abs(left.length - right.length),
                      first: differing.slice(0, 8).map((index) => ({
                        index, diagnostic: left[index], maintained: right[index],
                      })),
                    };
                  }
                }
                const contactMismatch = JSON.stringify(actual.contacts) !==
                  JSON.stringify(expected.contacts);
                const capture = {
                  event: solverInputTraceEvent,
                  substep: solverInputTraceSubstep,
                  solverInputExact: true,
                  solverOutputsExactlyMatchMaintainedArtifact:
                    Object.keys(outputDifferences).length === 0 &&
                    !contactMismatch,
                  contactMismatch,
                  outputDifferences,
                  solverOutputArrays: Object.fromEntries(
                    [...solverOutputFields].map((field) => [
                      field, actual.arrays[field] ?? [],
                    ])),
                  newtonTrace: activeNewtonTraces.at(-1),
                };
                fs.writeFileSync(solverInputTraceOutput,
                  `${JSON.stringify(capture)}\n`);
                console.log("EXACT MAINTAINED-ARTIFACT SOLVER TRACE " +
                  JSON.stringify({event: capture.event,
                    substep: capture.substep,
                    solverInputExact: capture.solverInputExact,
                    solverOutputsExactlyMatchMaintainedArtifact:
                      capture.solverOutputsExactlyMatchMaintainedArtifact,
                    contactMismatch,
                    outputDifferenceFields: Object.keys(outputDifferences)}));
                // The injected state is a diagnostic solver input, not a
                // coherent continuation of the candidate module's game state.
                // End this one-shot process after saving its exact-input result.
                process.exit(0);
              }
            } else {
              mujoco.mj_fwdConstraint(model, data);
            }
            capturePhase("fwdConstraint");
            data.flg_rnepost = 0;
            mujoco.mj_sensorAcc(model, data);
            capturePhase("sensorAcc");
            mujoco.mj_checkAcc(model, data);
            capturePhase("checkAcc");
            mujoco.mj_implicit(model, data);
            capturePhase("implicit");
          } else {
            mujoco.mj_step2(model, data);
          }
        };
      }
      game.substep = (dt) => {
        substep(dt);
        if (activeEngineSubsteps) {
          const snapshot = physicsSnapshot(game, replayEvents.length);
          activeEngineSubsteps.push(snapshot.engine);
          activeSubstepStates.push(snapshot);
        }
      };
      const advance = game.advance.bind(game);
      game.advance = (dt, held = []) => {
        const eventIndex = replayEvents.length;
        activeDiagnosticEvent = eventIndex;
        if (engineDiagnosticEvents.has(eventIndex)) {
          activeEngineSubsteps = [];
          activeSubstepStates = [];
          if (process.env.NW_MARBLE_PLAY_TRACE_SPLIT_STEP === "1") {
            activeStep1Substeps = [];
            activeStep1Inputs = [];
            if (process.env.NW_MARBLE_PLAY_TRACE_PHASES === "1") {
              activeStep1Phases = [];
              activeStep2Phases = [];
              activeRneTraces = [];
              activeRneAwakeStates = [];
              activeNewtonTraces = process.env.NW_MARBLE_PLAY_TRACE_NEWTON === "1"
                ? [] : null;
            }
          }
        }
        advance(dt, held);
        const event = {
          kind: "frame",
          dt,
          held: [...held].sort(),
        };
        if (tracePath || traceDirectory) event.state = physicsSnapshot(game, eventIndex);
        if (activeEngineSubsteps) {
          event.engineSubsteps = activeEngineSubsteps;
          event.substepStates = activeSubstepStates;
          if (activeStep1Substeps) {
            event.engineStep1Substeps = activeStep1Substeps;
            event.engineStep1Inputs = activeStep1Inputs;
            if (activeStep1Phases) event.engineStep1Phases = activeStep1Phases;
            if (activeStep2Phases) event.engineStep2Phases = activeStep2Phases;
            if (activeRneTraces?.length) {
              event.rneTraces = activeRneTraces;
              event.rneAwakeStates = activeRneAwakeStates;
            }
            if (activeNewtonTraces?.length) {
              event.newtonTraces = activeNewtonTraces;
            }
          }
          activeEngineSubsteps = null;
          activeSubstepStates = null;
          activeStep1Substeps = null;
          activeStep1Inputs = null;
          activeStep1Phases = null;
          activeStep2Phases = null;
          activeRneTraces = null;
          activeRneAwakeStates = null;
          activeNewtonTraces = null;
        }
        replayEvents.push(event);
      };
      const level = game.level.bind(game);
      game.level = () => {
        level();
        const event = { kind: "level" };
        if (tracePath || traceDirectory) event.state = physicsSnapshot(game, replayEvents.length);
        replayEvents.push(event);
      };
    }
    let controllerElapsedMs = 0;
    let settled = false;
    const controllerRunning = () =>
      readState(handle)[INFO.phase] === PHASE.running;

    const syncFrame = (dt = 1 / 60) => {
      // Match the production host: the physical simulation's cumulative clock
      // is authoritative; feed only its reached whole milliseconds to the
      // integer-millisecond controller. Independent dt accumulation can
      // cross a timeout one physics frame early due to floating-point sums.
      const targetWholeMs = Math.floor(game.elapsed * 1000);
      const currentMs = Number(readState(handle)[INFO.elapsedMs]);
      const wholeMs = Math.max(0, targetWholeMs - currentMs);
      if (wholeMs > 0) {
        assert.equal(advance(handle, wholeMs), STATUS.accepted);
        controllerElapsedMs += wholeMs;
      }
    };

    const steerTowardPoint = (target, maxCorrections, control = {}) => {
      const pulseFrames = control.pulseFrames ?? 6;
      const coastFrames = control.coastFrames ?? 18;
      const singleAxis = control.singleAxis ?? false;
      for (let correction = 0; correction < maxCorrections && !game.settled &&
           controllerRunning();
           correction++) {
        const marble = game.marbles.find((candidate) =>
          candidate.state === "rolling");
        if (!marble) return;
        const dx = target.x - marble.x;
        const dy = target.y - marble.y;
        if (Math.abs(dx) <= 0.008 && Math.abs(dy) <= 0.008 &&
            Math.hypot(marble.vx, marble.vy) <= 0.02) return;
        const directions = [];
        const xDirection = Math.abs(marble.vx) > 0.035 && marble.vx * dx > 0
          ? (dx > 0 ? "W" : "E") : (dx > 0 ? "E" : "W");
        const yDirection = Math.abs(marble.vy) > 0.035 && marble.vy * dy > 0
          ? (dy > 0 ? "S" : "N") : (dy > 0 ? "N" : "S");
        if (Math.abs(dx) > 0.006 || Math.abs(marble.vx) > 0.02) {
          directions.push(xDirection);
        }
        if (Math.abs(dy) > 0.006 || Math.abs(marble.vy) > 0.02) {
          directions.push(yDirection);
        }
        if (singleAxis && directions.length > 1) {
          const preferX = Math.abs(dx) + Math.abs(marble.vx) * 0.15 >=
            Math.abs(dy) + Math.abs(marble.vy) * 0.15;
          directions.splice(0, directions.length,
            preferX ? xDirection : yDirection);
        }
        for (const name of directions) {
          const inputStatus = dispatch(handle, EVENT.keyDown, KEY[name],
            { W: 65, N: 87, E: 68, S: 83 }[name]);
          const marbleStatus = game.marbles.map((ball) => ({
            state: ball.state,
            x: Number(ball.x.toFixed(4)),
            y: Number(ball.y.toFixed(4)),
            vx: Number(ball.vx.toFixed(4)),
            vy: Number(ball.vy.toFixed(4)),
          }));
          assert.equal(inputStatus, STATUS.accepted,
            `steering input rejected (rung ${testCase.rung}, seed ` +
            `${testCase.runSeed}, phase ${readState(handle)[INFO.phase]}, ` +
            `controller ${controllerElapsedMs}ms, physics ` +
            `${Math.round(game.elapsed * 1000)}ms, target ` +
            `${target.x.toFixed(4)},${target.y.toFixed(4)}, marbles ` +
            `${JSON.stringify(marbleStatus)})`);
        }
        for (let frame = 0; frame < pulseFrames && controllerRunning(); frame++) {
          game.advance(1 / 60, new Set(directions));
          syncFrame();
        }
        for (const name of directions) {
          assert.equal(dispatch(handle, EVENT.keyUp, KEY[name],
            { W: 65, N: 87, E: 68, S: 83 }[name]), STATUS.accepted);
        }
        if (!controllerRunning()) break;
        game.level();
        assert.equal(dispatch(handle, EVENT.action, ACTION.level), STATUS.accepted,
          `steering level update rejected (rung ${testCase.rung}, seed ` +
          `${testCase.runSeed}, phase ${readState(handle)[INFO.phase]}, ` +
          `controller ${controllerElapsedMs}ms, physics ` +
          `${Math.round(game.elapsed * 1000)}ms, target ` +
          `${target.x.toFixed(4)},${target.y.toFixed(4)}, ` +
          `correction ${correction}, home ${game.home}, lost ${game.lost})`);
        for (let frame = 0; frame < coastFrames && !game.settled &&
             controllerRunning(); frame++) {
          game.advance(1 / 60, new Set());
          syncFrame();
        }
      }
    };

    if (inputTrace) {
      let activeHeld = new Set();
      for (const [eventIndex, event] of inputTrace.events.entries()) {
        assert.ok(controllerRunning(),
          `current controller ended before replay input event ${eventIndex}`);
        if (event.kind === "frame") {
          const nextHeld = new Set(event.held);
          for (const name of activeHeld) {
            if (nextHeld.has(name)) continue;
            assert.equal(dispatch(handle, EVENT.keyUp, KEY[name],
              { W: 65, N: 87, E: 68, S: 83 }[name]), STATUS.accepted,
            `input-trace key-up rejected at event ${eventIndex}: ${name}`);
          }
          for (const name of nextHeld) {
            if (activeHeld.has(name)) continue;
            assert.equal(dispatch(handle, EVENT.keyDown, KEY[name],
              { W: 65, N: 87, E: 68, S: 83 }[name]), STATUS.accepted,
            `input-trace key-down rejected at event ${eventIndex}: ${name}`);
          }
          game.advance(event.dt, nextHeld);
          syncFrame(event.dt);
          activeHeld = nextHeld;
        } else {
          game.level();
          assert.equal(dispatch(handle, EVENT.action, ACTION.level), STATUS.accepted,
            `input-trace level action rejected at event ${eventIndex}`);
        }
        assert.ok(controllerRunning() || eventIndex === inputTrace.events.length - 1,
          `controller ended before input trace event ${eventIndex + 1}`);
      }
      assert.equal(replayEvents.length, inputTrace.events.length,
        "the replay must preserve every input-trace event");
      assert.ok(!controllerRunning(),
        "input trace ended before physical settlement or the 120-second timeout");
      settled = game.settled;
    } else if (testCase.expected === null) {
      let routeIndex = 0;
      let routeSegments = 0;
      let activeMarble = null;
      const coupledControl = board.starts.length > 1
        ? { pulseFrames: 16, coastFrames: 2, singleAxis: true }
        : {};
      while (routeIndex < route.length && routeSegments < 256 && !settled &&
             controllerRunning()) {
      const movingMarble = game.marbles.find((marble) =>
        marble.state === "rolling");
      if (!movingMarble) break;
      if (movingMarble !== activeMarble) {
        activeMarble = movingMarble;
        routePlan = findCellRoute(board, routePlan.cellOf(activeMarble));
        route = routePlan.route;
        routeIndex = 0;
      }
      routeSegments++;
      // The graph route is defined between cell centers. A marble may enter
      // a cell near a wall endpoint, where the nominal outgoing edge is
      // physically blocked by the finite-radius ball. Re-center before
      // following the next graph edge.
      steerTowardPoint(routePlan.cells[routeIndex],
        board.starts.length > 1 ? 0 : 40, coupledControl);
      if (game.settled) break;
      if (board.starts.length > 1) {
        // Do not hold a full direction for a long edge on a coupled tray: that
        // simultaneously accelerates every marble and can throw passive balls
        // through the outer rail. Make short, single-axis corrections toward
        // the next cell, then replan from the measured cell on the next pass.
        const target = routePlan.cells[Math.min(routeIndex + 1,
          routePlan.cells.length - 1)];
        steerTowardPoint(target, 2, coupledControl);
        if (game.settled) break;
        const current = game.marbles.find((marble) =>
          marble.state === "rolling");
        if (!current || current !== activeMarble) {
          activeMarble = null;
          continue;
        }
        const currentCell = routePlan.cellOf(current);
        const currentRouteIndex = routePlan.routeIndexOf(currentCell);
        if (process.env.NW_MARBLE_PLAY_DEBUG === "1" && routeSegments <= 20) {
          console.log("generated coupled steering step", JSON.stringify({
            routeSegments, target, currentCell, currentRouteIndex,
            marble: {x: current.x, y: current.y, vx: current.vx, vy: current.vy},
            home: game.home, lost: game.lost,
          }));
        }
        if (currentRouteIndex >= routeIndex + 1) {
          routeIndex = currentRouteIndex;
        } else if (currentRouteIndex < 0) {
          routePlan = findCellRoute(board, currentCell);
          route = routePlan.route;
          routeIndex = 0;
        }
        continue;
      }
      const name = route[routeIndex];
      const key = KEY[name];
      const physicalKey = { W: 65, N: 87, E: 68, S: 83 }[name];
      assert.equal(dispatch(handle, EVENT.keyDown, key, physicalKey),
        STATUS.accepted,
        `route key-down rejected (rung ${testCase.rung}, seed ` +
        `${testCase.runSeed}, phase ${readState(handle)[INFO.phase]}, ` +
        `controller ${controllerElapsedMs}ms, physics ` +
        `${Math.round(game.elapsed * 1000)}ms, segment ${routeSegments}, ` +
        `cell ${routePlan.cellOf(activeMarble)}, direction ${name})`);
      const edgeFrames = board.starts.length > 1 ? 24 : 18;
      for (let frame = 0; frame < edgeFrames && !game.settled &&
           controllerRunning(); frame++) {
        game.advance(1 / 60, new Set([name]));
        syncFrame();
        if (board.starts.length > 1) {
          const current = game.marbles.find((marble) =>
            marble.state === "rolling");
          if (!current || current !== activeMarble) break;
          const reached = routePlan.routeIndexOf(routePlan.cellOf(current));
          if (reached >= routeIndex + 1) break;
        }
      }
      if (!controllerRunning()) break;
      assert.equal(dispatch(handle, EVENT.keyUp, key, physicalKey),
        STATUS.accepted,
        `route key-up rejected (rung ${testCase.rung}, seed ` +
        `${testCase.runSeed}, phase ${readState(handle)[INFO.phase]}, ` +
        `controller ${controllerElapsedMs}ms, physics ` +
        `${Math.round(game.elapsed * 1000)}ms, segment ${routeSegments}, ` +
        `cell ${routePlan.cellOf(activeMarble)}, direction ${name})`);
      game.level();
      assert.equal(dispatch(handle, EVENT.action, ACTION.level), STATUS.accepted,
        `route level update rejected (rung ${testCase.rung}, seed ` +
        `${testCase.runSeed}, phase ${readState(handle)[INFO.phase]}, ` +
        `controller ${controllerElapsedMs}ms, physics ` +
        `${Math.round(game.elapsed * 1000)}ms, segment ${routeSegments}, ` +
        `settled ${game.settled}, home ${game.home}, lost ${game.lost})`);
      // Coupled boards need a short coast to dissipate velocity between edges.
      // Keep this bounded alongside the shorter, measured-cell pulse so long
      // multi-marble routes fit within the unchanged controller deadline.
      const routeCoastFrames = board.starts.length > 1 ? 4 : 36;
      for (let frame = 0; frame < routeCoastFrames && !game.settled &&
           controllerRunning(); frame++) {
        game.advance(1 / 60, new Set());
        syncFrame();
      }
      const nextMovingMarble = game.marbles.find((marble) =>
        marble.state === "rolling");
      if (nextMovingMarble !== activeMarble) {
        activeMarble = null;
        continue;
      }
      const currentCell = routePlan.cellOf(activeMarble);
      const currentRouteIndex = routePlan.routeIndexOf(currentCell);
      if (process.env.NW_MARBLE_PLAY_DEBUG === "1" && routeSegments <= 16) {
        console.log("generated play steering step", JSON.stringify({
          routeSegments,
          direction: name,
          before: routePlan.cells[routeIndex],
          currentCell,
          currentRouteIndex,
          marble: {x: activeMarble.x, y: activeMarble.y,
            vx: activeMarble.vx, vy: activeMarble.vy},
          home: game.home,
          lost: game.lost,
        }));
      }
      if (currentRouteIndex >= routeIndex + 1) {
        routeIndex = currentRouteIndex;
      } else {
        // The physical marble may not have reached the planned next cell:
        // momentum, wall contact, and cell discretization can invalidate a
        // static BFS path. Replan from the measured cell rather than issuing
        // stale directions from the original start.
        routePlan = findCellRoute(board, currentCell);
        route = routePlan.route;
        routeIndex = 0;
      }
      if (game.settled) {
        settled = true;
        break;
      }
      }

      // The cell path only gets the marble into the home cell. Aim at the
      // cup centre so capture is still decided by official MuJoCo physics.
      steerTowardPoint(board.home, board.starts.length > 1 ? 80 : 240,
        coupledControl);
      settled = game.settled;
    } else {
      // Keep the established, source-sized held route unchanged for the
      // already-certified regression cases.
      for (const name of route) {
        const key = KEY[name];
        const physicalKey = { W: 65, N: 87, E: 68, S: 83 }[name];
        assert.equal(dispatch(handle, EVENT.keyDown, key, physicalKey),
          STATUS.accepted);
        for (let frame = 0; frame < 18 && !game.settled; frame++) {
          game.advance(1 / 60, new Set([name]));
          syncFrame();
        }
        assert.equal(dispatch(handle, EVENT.keyUp, key, physicalKey),
          STATUS.accepted);
        game.level();
        assert.equal(dispatch(handle, EVENT.action, ACTION.level), STATUS.accepted);
        for (let frame = 0; frame < 36 && !game.settled; frame++) {
          game.advance(1 / 60, new Set());
          syncFrame();
        }
        if (game.settled) {
          settled = true;
          break;
        }
      }
    }

    // The source keeps stepping physics after the route follower has no
    // rolling marble left to steer (for example, while a swallowed marble is
    // still in its falling animation). Continue with neutral input until the
    // physical tray settles or the authoritative board timer expires.
    while (!game.settled && controllerRunning()) {
      game.advance(1 / 60, new Set());
      syncFrame();
    }
    settled = game.settled;

    const timedOut = readState(handle)[INFO.phase] === PHASE.feedback;
    if (!settled && !timedOut) {
      console.error("generated play terminal diagnostic", {
        rung: testCase.rung,
        runSeed: testCase.runSeed,
        route,
        leadCell: routePlan.cellOf(game.marbles[0]),
        routeCells: routePlan.cells,
        start: board.starts[0],
        home: board.home,
        elapsed: game.elapsed,
        marbles: game.marbles.map((marble) => ({
          x: marble.x, y: marble.y, vx: marble.vx, vy: marble.vy,
          state: marble.state,
        })),
      });
    }
    assert.ok(settled || timedOut,
      `generated route neither settled nor reached the source timeout ` +
      `(rung ${testCase.rung}, run seed ${testCase.runSeed}, route ${route})`);
    if (timedOut) outcomeCounts.timeout++;
    else if (game.won) outcomeCounts.won++;
    else if (game.lost > 0) outcomeCounts.physicalLoss++;
    else assert.fail(
      `settled generated play had neither home nor lost marbles ` +
      `(rung ${testCase.rung}, run seed ${testCase.runSeed})`);
    // The original task treats expiry as a loss even when all marbles happen
    // to reach home on the final physics frame. Its result row still records
    // the host's actual home/lost counts at expiry.
    const physicalVerdict = game.won && !timedOut ? 1 : 0;
    const scoreWin = game.lost === 0 ? 1 : 0;
    const resultBits = physicalVerdict | (scoreWin << 1);
    assert.equal(dispatch(handle, EVENT.action, ACTION.syncSettleTime,
      Math.round(game.elapsed * 1000)), STATUS.accepted);
    if (timedOut) {
      assert.equal(dispatch(handle, EVENT.action, ACTION.score, scoreWin),
        STATUS.accepted);
    } else {
      assert.equal(dispatch(handle, EVENT.action, ACTION.report, resultBits,
        Math.round((board.route / 0.25 + 2.5 * game.marbles.length) * 1000)),
      STATUS.accepted);
    }
    assert.equal(dispatch(handle, EVENT.action, ACTION.recordResult,
      game.home, game.lost), STATUS.accepted);
    assert.equal(advance(handle, 2600), STATUS.accepted);
    state = readState(handle);
    assert.equal(state[INFO.phase], PHASE.done);
    assert.equal(state[INFO.trial], 1n);
    assert.equal(resultValue(handle, RESULT.rung), BigInt(testCase.rung));
    assert.equal(resultValue(handle, RESULT.elapsedMs),
      BigInt(Math.round(game.elapsed * 1000)));
    assert.equal(resultValue(handle, RESULT.home), BigInt(game.home));
    assert.equal(resultValue(handle, RESULT.lost), BigInt(game.lost));
    assert.equal(resultValue(handle, RESULT.verdict), BigInt(physicalVerdict));
    assert.equal(resultValue(handle, RESULT.scoreWin), BigInt(scoreWin));
    assert.equal(resultValue(handle, RESULT.boardSeed), state[INFO.seed]);
    if (testCase.expected !== null) {
      assert.equal(testCase.expected, game.won ? "won" : "lost");
    } else {
      assert.ok(game.won || game.lost > 0 || timedOut,
        `exhaustive generated play did not produce a terminal outcome ` +
        `(rung ${testCase.rung}, run seed ${testCase.runSeed})`);
    }
    if (replayEvents) {
      const destination = tracePath ?? `${traceDirectory}/${testCase.rung}-${testCase.runSeed}.json`;
      fs.writeFileSync(destination, `${JSON.stringify({
        version: 1,
        runtimeProvenance,
        rung: testCase.rung,
        runSeed: testCase.runSeed,
        boardSeed,
        timeLimitMs: 120000,
        contactDiagnostics: process.env.NW_MARBLE_PLAY_TRACE_CONTACTS === "1",
        engineDiagnosticEvents: [...engineDiagnosticEvents],
        outcome: timedOut ? "timeout" : game.won ? "won" : "physical-loss",
        result: {
          elapsedMs: Number(resultValue(handle, RESULT.elapsedMs)),
          home: game.home,
          lost: game.lost,
          verdict: physicalVerdict,
          scoreWin,
        },
        ...(inputTraceIdentity ? { inputTraceReplay: inputTraceIdentity } : {}),
        events: replayEvents,
      })}\n`);
    }
  } finally {
    if (game) game.disposeEngine();
    if (!destroyed) {
      assert.equal(exports.nw_api_v1_destroy(handle), 0n);
      destroyed = true;
    }
    const resources = resourceStats();
    assert.equal(resources.liveModels, resourceBaseline.liveModels,
      `MuJoCo model leak in generated play case ${testCase.runSeed}`);
    assert.equal(resources.liveData, resourceBaseline.liveData,
      `MuJoCo data leak in generated play case ${testCase.runSeed}`);
  }
}

assert.equal(outcomeCounts.won + outcomeCounts.physicalLoss +
  outcomeCounts.timeout, cases.length,
  "generated play outcome buckets must account for every case exactly once");
console.log(`PASS: generated Marble held-input play sessions (${cases.length} ` +
  `cases; ${outcomeCounts.won} won, ${outcomeCounts.physicalLoss} physical losses, ` +
  `${outcomeCounts.timeout} timeouts; controller ` +
  "result history and cleanup)");
