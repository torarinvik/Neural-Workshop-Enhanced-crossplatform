"""Actual original enclosing implicitfast outputs on owned exact read-set copies.

Synchronized localization only; never ordinary trajectory acceptance.
"""
import argparse
import ctypes
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

from marble_integrator_readset import validated_packet, named_phase, INTEGER_MODEL, DIMENSIONS
from marble_primal_eval_oracle import OriginalEval, ORIGINAL_EVAL_OFFSET, DlInfo, REFERENCE_SHA256


def bits(values):
    return [struct.pack(">d", float(value)).hex() for value in values]


class OriginalIntegrator:
    def __init__(self, path):
        self.anchor = OriginalEval(path)
        base = ctypes.cast(self.anchor.routine, ctypes.c_void_p).value - ORIGINAL_EVAL_OFFSET
        self.routine = self.anchor.library.mj_implicit
        address = ctypes.cast(self.routine, ctypes.c_void_p).value
        dladdr = ctypes.CDLL(None).dladdr
        dladdr.argtypes = [ctypes.c_void_p, ctypes.POINTER(DlInfo)]
        dladdr.restype = ctypes.c_int
        info = DlInfo()
        if address != base + 0x88328 or not dladdr(address, ctypes.byref(info)) or not info.filename or Path(info.filename.decode()).resolve() != self.anchor.path:
            raise ValueError("original implicit symbol/image/address differs")
        self.routine.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.routine.restype = None
        self.position = self.anchor.library.mj_integratePos
        position_address=ctypes.cast(self.position,ctypes.c_void_p).value
        position_info=DlInfo()
        if position_address != base+0x10970c or not dladdr(position_address,ctypes.byref(position_info)) or not position_info.filename or Path(position_info.filename.decode()).resolve() != self.anchor.path:
            raise ValueError("original position symbol/image/address differs")
        self.position.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_double),ctypes.POINTER(ctypes.c_double),ctypes.c_double]
        self.position.restype=None
        ptr=ctypes.POINTER(ctypes.c_double)
        for name,offset,signature,result in (
            ("mjd_freeBias_vel",0x669f8,[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ptr],None),
            ("mjd_freeMhat",0x66f80,[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_double,ptr],ctypes.c_int),
            ("mju_factorLU6",0x11ecec,[ptr,ctypes.POINTER(ctypes.c_int)],ctypes.c_int),
            ("mju_solveLU6",0x11ef2c,[ptr,ptr,ptr,ctypes.POINTER(ctypes.c_int)],None)):
            routine=getattr(self.anchor.library,name);address=ctypes.cast(routine,ctypes.c_void_p).value
            info=DlInfo()
            if address!=base+offset or not dladdr(address,ctypes.byref(info)) or not info.filename or Path(info.filename.decode()).resolve()!=self.anchor.path:
                raise ValueError("original local solve image/address differs: "+name)
            routine.argtypes=signature;routine.restype=result

    def advance_position(self,model,before,after):
        inputs=validated_packet(before,"checkAcc")
        outputs=validated_packet(after,"implicit")
        for key in DIMENSIONS:
            if getattr(model,key) != before["dimensions"][key]: raise ValueError("position model dimensions differ")
        for key in INTEGER_MODEL:
            if getattr(model,key).ravel().tolist() != before["model"][key]: raise ValueError("position model layout differs")
        qpos=(ctypes.c_double*len(inputs["arrays"]["qpos"]))(*inputs["arrays"]["qpos"])
        qvel=(ctypes.c_double*len(outputs["outputs"]["qvel"]))(*outputs["outputs"]["qvel"])
        self.position(ctypes.c_void_p(int(model._address)),qpos,qvel,inputs["options"]["timestep"])
        if bits(qvel) != after["outputBits"]["qvel"]: raise ValueError("position call mutated velocity")
        if any(not math.isfinite(value) for value in qpos): raise ValueError("position call returned nonfinite values")
        for joint in range(before["dimensions"]["njnt"]):
            for axis in range(3):
                expected=math.fma(inputs["options"]["timestep"],
                                  outputs["outputs"]["qvel"][6*joint+axis],
                                  inputs["arrays"]["qpos"][7*joint+axis])
                if bits([qpos[7*joint+axis]])!=bits([expected]):
                    raise ValueError("original free translation FMA ordering differs")
        # Translation-only finite operand stress. Quaternion results are not
        # claimed qualified by these calls; angular velocities remain zero.
        for case in range(50):
            positions=list(inputs["arrays"]["qpos"])
            velocities=[0.]*len(outputs["outputs"]["qvel"])
            dt=2.**(-4-case%12)
            for joint in range(before["dimensions"]["njnt"]):
                for axis in range(3):
                    positions[7*joint+axis]=math.sin(case*9+joint*3+axis+.1)*2.**(case%17-8)
                    velocities[6*joint+axis]=math.cos(case*7+joint*3+axis+.2)*2.**(case%13-6)
            qp=(ctypes.c_double*len(positions))(*positions)
            qv=(ctypes.c_double*len(velocities))(*velocities)
            self.position(ctypes.c_void_p(int(model._address)),qp,qv,dt)
            if bits(qv)!=bits(velocities):raise ValueError("translation stress mutated velocity")
            for joint in range(before["dimensions"]["njnt"]):
                for axis in range(3):
                    expected=math.fma(dt,velocities[6*joint+axis],positions[7*joint+axis])
                    if bits([qp[7*joint+axis]])!=bits([expected]):
                        raise ValueError("original translation stress FMA differs")
        return bits(qpos)

    def evaluate(self, model, data, packet):
        operands = validated_packet(packet, "checkAcc")
        # Complete checks precede any model/data writes.
        for key in DIMENSIONS:
            if getattr(model, key) != packet["dimensions"][key]:
                raise ValueError("original integration model dimension differs: " + key)
        for key in INTEGER_MODEL:
            if getattr(model, key).ravel().tolist() != packet["model"][key]:
                raise ValueError("original integration topology/layout differs: " + key)
        for owner, arrays in ((model, operands["model"]), (data, operands["arrays"])):
            for key, values in arrays.items():
                if getattr(owner, key).size != len(values):
                    raise ValueError("owned integration operand size differs: " + key)
        for owner, arrays in ((model, operands["model"]), (data, operands["arrays"])):
            for key, values in arrays.items():
                getattr(owner, key).ravel()[:] = values
                if bits(getattr(owner,key).ravel()) != bits(values):
                    raise ValueError("integration operand copy differs: " + key)
        for key in ("integrator", "disableflags", "enableflags"):
            setattr(model.opt,key,packet["options"][key])
            if getattr(model.opt,key) != packet["options"][key]: raise ValueError("integration flag copy differs")
        for key,value in operands["options"].items():
            setattr(model.opt,key,value)
            if bits([getattr(model.opt,key)]) != bits([value]):
                raise ValueError("integration option copy differs")
        data.time = operands["time"]
        if bits([data.time]) != bits([operands["time"]]): raise ValueError("integration time copy differs")
        self.routine(ctypes.c_void_p(int(model._address)), ctypes.c_void_p(int(data._address)))
        outputs = {key:getattr(data,key).ravel().tolist() for key in ("qpos","qvel","qacc_warmstart","qDeriv","qH","qHDiagInv")}
        if not math.isfinite(data.time) or any(not math.isfinite(value) for values in outputs.values() for value in values):
            raise ValueError("original integration returned nonfinite outputs")
        for key,values in operands["arrays"].items():
            if key not in ("qpos","qvel") and bits(getattr(data,key).ravel()) != bits(values):
                raise ValueError("original integration mutated read-only input: " + key)
        # qDeriv is now assigned by the complete original integration call.
        # Restore pre-call velocity for an independent public local-solve check.
        data.qvel[:]=operands["arrays"]["qvel"]
        local=[];local_stages=[];lib=self.anchor.library
        for joint in range(model.njnt):
            matrix=(ctypes.c_double*36)();pivot=(ctypes.c_int*6)()
            bias=(ctypes.c_double*36)()
            lib.mjd_freeBias_vel(ctypes.c_void_p(int(model._address)),ctypes.c_void_p(int(data._address)),joint,bias)
            if not lib.mjd_freeMhat(ctypes.c_void_p(int(model._address)),ctypes.c_void_p(int(data._address)),joint,model.opt.timestep,matrix):
                raise ValueError("original standalone free solve unexpectedly ineligible")
            lu=(ctypes.c_double*36)(*matrix)
            if not lib.mju_factorLU6(lu,pivot): raise ValueError("original standalone free solve singular")
            adr=6*joint
            rhs=(ctypes.c_double*6)(*(operands["arrays"]["qfrc_smooth"][adr+i]+operands["arrays"]["qfrc_constraint"][adr+i] for i in range(6)))
            solved=(ctypes.c_double*6)();lib.mju_solveLU6(solved,lu,rhs,pivot)
            local.extend(solved)
            local_stages.append(dict(joint=joint,matrixBits=bits(matrix),luBits=bits(lu),
                                     biasBits=bits(bias),pivots=list(pivot),rhsBits=bits(rhs),solutionBits=bits(solved)))
        advanced=[math.fma(a,model.opt.timestep,v) for a,v in zip(local,operands["arrays"]["qvel"])]
        if bits(advanced)!=bits(outputs["qvel"]):
            raise ValueError("original public local solve plus FMA does not qualify enclosing velocity")
        return dict(time=float(data.time), timeBits=bits([data.time])[0], outputs=outputs,
                    outputBits={key:bits(values) for key,values in outputs.items()},
                    originalPublicLocalAccelerationBits=bits(local),originalPublicLocalStages=local_stages,
                    originalPublicLocalSolveAdvanceQualified=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace",type=Path)
    parser.add_argument("--reference-library",type=Path,required=True)
    parser.add_argument("--source-root",type=Path,required=True)
    args=parser.parse_args()
    trace=json.loads(args.trace.read_text())
    rows=[]
    for event_index,event in enumerate(trace["events"]):
        for substep in range(len(event.get("engineStep2Phases",[]))):
            before=named_phase(event,substep,"checkAcc")["engine"]["integratorReadSet"]
            after=named_phase(event,substep,"implicit")["engine"]["integratorReadSet"]
            validated_packet(before,"checkAcc");validated_packet(after,"implicit")
            for key in ("dimensions","model","modelBits","options","optionBits"):
                if before[key] != after[key]: raise ValueError("integration static operands mutated")
            rows.append((event_index,substep,before,after))
    if not rows: raise ValueError("no complete integration boundaries")
    original=OriginalIntegrator(args.reference_library)
    import mujoco
    from marble_source_play_trace import native_mujoco_provenance
    native=native_mujoco_provenance(mujoco)
    if native["activeEngineLibrary"]["sha256"] != REFERENCE_SHA256 or Path(native["activeEngineLibrary"]["path"]).resolve() != original.anchor.path:
        raise ValueError("owned integration models require actual original wheel")
    sys.path.insert(0,str(args.source_root.resolve()))
    from neural_workshop import marblemaze as source
    from marble_source_capture import float32_abi_tray
    sim=source.Simulation(float32_abi_tray(source.deal(trace["rung"],seed=trace["boardSeed"])))
    sim._ensure_engine()
    report=[]
    for event,substep,before,after in rows:
        actual=original.evaluate(sim._model,sim._data,before)
        position_bits=original.advance_position(sim._model,before,after)
        position_differences=[dict(index=i,original=x,browser=y) for i,(x,y) in enumerate(zip(position_bits,after["outputBits"]["qpos"])) if x != y]
        differences={key:[dict(index=i,original=x,browser=y) for i,(x,y) in enumerate(zip(actual["outputBits"][key],after["outputBits"][key])) if x != y] for key in actual["outputBits"]}
        differences={key:values for key,values in differences.items() if values}
        if actual["timeBits"] != after["timeBits"]: differences["time"]=[dict(original=actual["timeBits"],browser=after["timeBits"])]
        report.append(dict(event=event,substep=substep,actualOriginal=actual,differences=differences,positionOnBrowserVelocityBits=position_bits,positionOnBrowserVelocityDifferences=position_differences))
    print(json.dumps(dict(schema="neural-workshop.marble-original-integrator.v1",traceSha256=hashlib.sha256(args.trace.read_bytes()).hexdigest(),referenceSha256=REFERENCE_SHA256,nativeRuntime=native,boundaries=report,differentBoundaries=sum(bool(r["differences"]) for r in report),differentValues=sum(len(v) for r in report for v in r["differences"].values()),matchedInputBits=True,ordinaryTrajectoryAcceptance=False,promoted=False),indent=2,allow_nan=False))


if __name__ == "__main__": main()
