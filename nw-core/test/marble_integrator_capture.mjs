// Read-only, opt-in integration operands. Preserve signed zero in IEEE bits.
export const integratorDimensions = ["nq", "nv", "na", "nu", "nbody", "njnt", "ntree", "nD", "nC", "nactuator", "nsensor", "nhistory", "nplugin", "nflex", "ntendon"];
export const integratorIntegerModel = ["body_parentid", "body_dofadr", "body_dofnum", "body_jntadr", "body_jntnum", "jnt_type", "jnt_bodyid", "jnt_dofadr", "jnt_qposadr", "dof_treeid", "tree_dofnum", "dof_jntid", "M_rownnz", "M_rowadr", "M_colind", "D_rownnz", "D_rowadr", "D_colind", "D_diag", "mapD2M"];
export const integratorFloatModel = ["body_mass", "body_subtreemass", "body_inertia", "dof_damping", "dof_dampingpoly"];
export const integratorInputs = ["qpos", "qvel", "qacc", "qfrc_smooth", "qfrc_constraint", "M", "xpos", "xipos", "xmat", "ximat", "tree_awake"];
export const integratorOutputs = ["qpos", "qvel", "qacc_warmstart", "qDeriv", "qH", "qHDiagInv"];

export function integratorBits(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error("nonfinite integration operand");
  const bytes = Buffer.alloc(8);
  bytes.writeDoubleBE(value);
  return bytes.toString("hex");
}

function array(object, field) {
  if (!ArrayBuffer.isView(object[field])) throw new Error(`missing integration array: ${field}`);
  const values = Array.from(object[field], Number);
  if (!values.every(Number.isFinite)) throw new Error(`nonfinite integration array: ${field}`);
  return values;
}

export function captureIntegrator(model, data, phase) {
  if (!["checkAcc", "implicit"].includes(phase)) throw new Error("invalid integration phase");
  const dimensions = Object.fromEntries(integratorDimensions.map((key) => {
    const value = Number(model[key]);
    if (!Number.isSafeInteger(value) || value < 0) throw new Error(`invalid integration dimension: ${key}`);
    return [key, value];
  }));
  const staticArrays = Object.fromEntries([...integratorIntegerModel, ...integratorFloatModel].map((key) => [key, array(model, key)]));
  const arrays = Object.fromEntries(integratorInputs.map((key) => [key, array(data, key)]));
  const options = Object.fromEntries(["integrator", "disableflags", "enableflags", "density", "viscosity", "timestep"].map((key) => [key, Number(model.opt[key])]));
  const outputs = phase === "implicit" ? Object.fromEntries(integratorOutputs.map((key) => [key, array(data, key)])) : null;
  return {
    schema: "neural-workshop.marble-integrator-readset.v1", phase, dimensions,
    model: staticArrays,
    modelBits: Object.fromEntries(integratorFloatModel.map((key) => [key, staticArrays[key].map(integratorBits)])),
    options, optionBits: Object.fromEntries(["density", "viscosity", "timestep"].map((key) => [key, integratorBits(options[key])])),
    time: Number(data.time), timeBits: integratorBits(Number(data.time)),
    arrays, arrayBits: Object.fromEntries(integratorInputs.map((key) => [key, arrays[key].map(integratorBits)])),
    outputs, outputBits: outputs && Object.fromEntries(integratorOutputs.map((key) => [key, outputs[key].map(integratorBits)])),
  };
}
