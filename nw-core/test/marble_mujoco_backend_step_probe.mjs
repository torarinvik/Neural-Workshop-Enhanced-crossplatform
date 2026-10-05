// Re-run one recorded Marble input event with an alternate MuJoCo WASM module.
// Before the probe event, restore the baseline WASM wrapper state and
// qacc_warmstart so native replay can compare one matched event/substep.
import fs from "node:fs";
import { pathToFileURL } from "node:url";
import { instantiateElisa } from "../shells/web/elisa-wasm-runtime.js";
import { decodeMarbleBoard } from "../shells/web/marble-maze.js";
import { loadMarbleMazeMuJoCo } from "../shells/web/marble-maze-mujoco.js";

const inputPath = process.env.NW_MARBLE_BASE_TRACE;
const outputPath = process.env.NW_MARBLE_PROBE_TRACE;
const modulePath = process.env.NW_MUJOCO_WASM_MODULE;
const targetIndex = Number(process.env.NW_MARBLE_PROBE_EVENT ?? 215);
if (!inputPath || !outputPath || !modulePath || !Number.isInteger(targetIndex) || targetIndex < 1) {
  throw new Error("set NW_MARBLE_BASE_TRACE, NW_MARBLE_PROBE_TRACE, NW_MUJOCO_WASM_MODULE, and a positive NW_MARBLE_PROBE_EVENT");
}
const baseline = JSON.parse(fs.readFileSync(inputPath, "utf8"));
if (!baseline.events[targetIndex]?.state || !baseline.events[targetIndex - 1]?.state) {
  throw new Error(`baseline trace needs full states before and at event ${targetIndex}`);
}
const wasmPath = process.env.NWCORE_WASM_PATH ??
  new URL("../build/nwcore.wasm", import.meta.url);
const { exports, instance } = await instantiateElisa(
  fs.readFileSync(wasmPath), { warn: false });
const pointer = Number(exports.nw_frame_alloc(65536n));
const length = Number(exports.nw_marble_board_write(
  BigInt(pointer), 65536n, BigInt(baseline.rung), BigInt(baseline.boardSeed)));
if (length <= 0) throw new Error("could not rebuild the baseline Marble board");
const board = decodeMarbleBoard(new Uint8Array(
  instance.exports.memory.buffer, pointer, length));
const loader = async () => {
  const module = await import(pathToFileURL(modulePath).href);
  return module.default();
};
const Game = await loadMarbleMazeMuJoCo(loader);
const game = new Game(board);

function restore(snapshot) {
  for (const [marble, value] of game.marbles.map((item, index) => [item, snapshot.marbles[index]])) {
    [marble.x, marble.y, marble.z, marble.vx, marble.vy, marble.vz,
      marble.qw, marble.qx, marble.qy, marble.qz,
      marble.wx, marble.wy, marble.wz] = value.values;
    marble.state = value.state;
    marble.over = value.over === null ? null : board.holes[value.over];
  }
  for (const field of ["roll", "pitch", "elapsed", "struckThisStep",
    "cuppedThisStep", "lostThisStep", "nudgeDue"]) {
    const key = ({struckThisStep: "struck", cuppedThisStep: "cupped",
      lostThisStep: "lostThisStep", nudgeDue: "nudgeDue"})[field] ?? field;
    game[field] = snapshot[key];
  }
  if (snapshot.qaccWarmstart) game.data.qacc_warmstart.set(snapshot.qaccWarmstart);
}

for (let index = 0; index < targetIndex; index++) {
  const event = baseline.events[index];
  if (event.kind === "level") game.level();
  else game.advance(event.dt, event.held);
}
restore(baseline.events[targetIndex - 1].state);

const fields = ["cvel", "cdof", "cdof_dot", "cacc", "cfrc_ext", "cfrc_int",
  "cinert", "crb", "subtree_com", "xpos", "xquat", "xipos", "ximat",
  "qpos", "qvel", "qacc", "qacc_smooth", "qacc_warmstart",
  "qfrc_constraint", "qfrc_smooth", "qfrc_bias", "qfrc_passive",
  "qfrc_applied", "qH", "qHDiagInv", "qLDiagInv", "qDeriv",
  "efc_force", "efc_pos", "efc_vel", "efc_aref", "efc_b", "efc_state",
  "efc_type", "efc_id", "efc_island", "efc_frictionloss", "efc_J",
  "efc_AR",
  "efc_KBIP", "efc_D", "efc_R", "solver_niter", "solver_nnz",
  "solver_fwdinv", "geom_xpos", "geom_xmat"];
function engineSnapshot() {
  return {
    time: Number(game.data.time), ncon: Number(game.data.ncon),
    nefc: Number(game.data.nefc),
    awake: {apiType: typeof game.mujoco.marbleAwakeState,
      state: typeof game.mujoco.marbleAwakeState === "function"
        ? game.mujoco.marbleAwakeState(game.model, game.data) : null},
    contacts: Array.from({length: Number(game.data.ncon)}, (_, index) => {
      const c = game.data.contact.get(index);
      return {geom1: Number(c.geom1), geom2: Number(c.geom2), dist: Number(c.dist),
        pos: Array.from(c.pos, Number), dim: Number(c.dim), mu: Number(c.mu),
        friction: Array.from(c.friction, Number)};
    }),
    arrays: Object.fromEntries(fields.map((field) => [
      field, Array.from(game.data[field] ?? [], Number)])),
    model: {gravity: Array.from(game.model.opt.gravity, Number),
      timestep: Number(game.model.opt.timestep),
      geom_bodyid: Array.from(game.model.geom_bodyid, Number),
      body_rootid: Array.from(game.model.body_rootid, Number),
      body_parentid: Array.from(game.model.body_parentid, Number),
      body_dofadr: Array.from(game.model.body_dofadr, Number),
      body_dofnum: Array.from(game.model.body_dofnum, Number),
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
      dof_jntid: Array.from(game.model.dof_jntid, Number)},
  };
}
const engineSubsteps = [];
const rneTraces = [];
const rneAwakeStates = [];
const rneInputs = [];
const rneInputSnapshots = [];
const engineStep1Phases = [];
if (process.env.NW_MARBLE_TRACE_RNE_LOCALS === "1" ||
    process.env.NW_MARBLE_TRACE_PHASES === "1") {
  const mujoco = game.mujoco;
  const originalStep = mujoco.mj_step.bind(mujoco);
  mujoco.mj_step = (model, data) => {
    const phases = [];
    const capturePhase = (phase) => {
      if (process.env.NW_MARBLE_TRACE_PHASES === "1") {
        phases.push({phase, engine: engineSnapshot()});
      }
    };
    mujoco.mj_checkPos(model, data);
    capturePhase("checkPos");
    mujoco.mj_checkVel(model, data);
    capturePhase("checkVel");
    mujoco.mj_kinematics(model, data);
    capturePhase("kinematics");
    mujoco.mj_comPos(model, data);
    capturePhase("comPos");
    mujoco.mj_fwdPosition(model, data);
    capturePhase("fwdPosition");
    mujoco.mj_sensorPos(model, data);
    capturePhase("sensorPos");
    capturePhase("probe_input");
    mujoco.mj_comVel(model, data);
    capturePhase("probe_comVel");
    mujoco.mj_passive(model, data);
    capturePhase("probe_passive");
    mujoco.mj_referenceConstraint(model, data);
    capturePhase("probe_referenceConstraint");
    if (typeof mujoco.marbleAwakeState === "function") {
      rneAwakeStates.push(mujoco.marbleAwakeState(game.model, data));
    }
    rneInputs.push({cvel: Array.from(data.cvel, Number),
      cinert: Array.from(data.cinert, Number)});
    rneInputSnapshots.push(engineSnapshot());
    if (typeof mujoco.marbleRneTrace === "function") {
      rneTraces.push(Array.from(mujoco.marbleRneTrace(model, data), Number));
    } else {
      mujoco.mj_rne(model, data, 0, data.qfrc_bias);
    }
    capturePhase("probe_rneBias");
    if (process.env.NW_MARBLE_TRACE_PHASES === "1") {
      const probeData = new mujoco.MjData(model, data);
      const liveData = game.data;
      game.data = probeData;
      try {
        probeData.qacc.fill(0);
        mujoco.mj_rnePostConstraint(model, probeData);
        capturePhase("probe_rnePostConstraint_zeroacc");
      } finally {
        game.data = liveData;
        probeData.delete();
      }
    }
    mujoco.mj_fwdVelocity(model, data);
    capturePhase("fwdVelocity");
    mujoco.mj_sensorVel(model, data);
    capturePhase("sensorVel");
    mujoco.mj_step2(model, data);
    if (process.env.NW_MARBLE_TRACE_PHASES === "1") {
      engineStep1Phases.push(phases);
    }
  };
  void originalStep;
}
const substep = game.substep.bind(game);
game.substep = (dt) => {
  substep(dt);
  engineSubsteps.push(engineSnapshot());
};
const event = baseline.events[targetIndex];
if (event.kind === "level") game.level();
else game.advance(event.dt, event.held);
const events = baseline.events.slice(0, targetIndex + 1).map((item, index) =>
  index === targetIndex ? {...item, engineSubsteps,
    ...(rneInputSnapshots.length ? {rneInputSnapshots, rneInputs} : {}),
    ...(rneTraces.length ? {rneTraces, rneAwakeStates} : {}),
    ...(engineStep1Phases.length ? {engineStep1Phases} : {})} : item);
fs.writeFileSync(outputPath, `${JSON.stringify({...baseline,
  engineDiagnosticEvents: [targetIndex], events})}\n`);
game.disposeEngine();
console.log(`Captured alternate MuJoCo state at baseline event ${targetIndex} (${engineSubsteps.length} physics substeps)`);
