import copy
import math
import struct
import unittest
from marble_integrator_readset import named_phase, decoded_bits, validated_packet, DIMENSIONS


class IntegratorReadSetTests(unittest.TestCase):
    def packet(self):
        d = dict.fromkeys(DIMENSIONS, 0)
        d.update(nq=7,nv=6,nbody=2,njnt=1,ntree=1,nD=36,nC=6)
        m = dict(body_parentid=[0,0],body_dofadr=[-1,0],body_dofnum=[0,6],body_jntadr=[-1,0],body_jntnum=[0,1],jnt_type=[0],jnt_bodyid=[1],jnt_dofadr=[0],jnt_qposadr=[0],dof_treeid=[0]*6,tree_dofnum=[6],dof_jntid=[0]*6,M_rownnz=[1]*6,M_rowadr=list(range(6)),M_colind=list(range(6)),D_rownnz=[6]*6,D_rowadr=list(range(0,36,6)),D_colind=list(range(6))*6,D_diag=list(range(6)),mapD2M=list(range(0,36,7)))
        floats = dict(body_mass=[0.,1.],body_subtreemass=[1.,1.],body_inertia=[0.]*6,dof_damping=[0.]*6,dof_dampingpoly=[0.]*12)
        m.update(floats)
        bits = lambda arrays: {key:[struct.pack(">d",v).hex() for v in values] for key,values in arrays.items()}
        arrays = {key:[0.]*size for key,size in (("qpos",7),("qvel",6),("qacc",6),("qfrc_smooth",6),("qfrc_constraint",6),("M",6),("xpos",6),("xipos",6),("xmat",18),("ximat",18),("tree_awake",1))}
        arrays["tree_awake"]=[1.]
        return dict(schema="neural-workshop.marble-integrator-readset.v1",phase="checkAcc",dimensions=d,model=m,modelBits=bits(floats),arrays=arrays,arrayBits=bits(arrays),options=dict(integrator=3,disableflags=0,enableflags=0,density=0.,viscosity=0.,timestep=.01),optionBits={key:struct.pack(">d",value).hex() for key,value in dict(density=0.,viscosity=0.,timestep=.01).items()},time=0.,timeBits="0000000000000000",outputs=None,outputBits=None)

    def test_complete_packet_sizes_and_model_layout(self):
        packet = self.packet()
        self.assertEqual(len(validated_packet(packet,"checkAcc")["arrays"]["xmat"]),18)
        for key in packet["arrays"]:
            bad=copy.deepcopy(packet);bad["arrays"][key].pop()
            with self.subTest(key=key),self.assertRaises(ValueError):validated_packet(bad,"checkAcc")

    def test_original_call_rejects_bad_packet_before_native_access(self):
        from marble_integrator_original import OriginalIntegrator
        original=OriginalIntegrator.__new__(OriginalIntegrator)
        bad=self.packet();bad["arrays"]["xmat"].pop()
        with self.assertRaises(ValueError):original.evaluate(None,None,bad)

    def test_unsupported_branches_and_bad_sparse_layout_reject(self):
        for container,key,value in (("dimensions","nplugin",1),("options","enableflags",16),("options","integrator",2),("model","D_diag",[0]*6),("model","mapD2M",[36]*6),("model","body_parentid",[0,1])):
            bad=self.packet();bad[container][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):validated_packet(bad,"checkAcc")

    def event(self):
        return {"engineStep2Phases": [[{"phase": "implicit", "engine": {}}, {"phase": "checkAcc", "engine": {"marker": 1}}]]}

    def test_named_owner_does_not_depend_on_position(self):
        self.assertEqual(named_phase(self.event(), 0, "checkAcc")["engine"], {"marker": 1})

    def test_missing_duplicate_and_invalid_owner_reject(self):
        for mutation in ("missing", "duplicate", "invalid"):
            event = self.event()
            phases = event["engineStep2Phases"][0]
            if mutation == "missing": phases.pop()
            elif mutation == "duplicate": phases.append(copy.deepcopy(phases[-1]))
            else: phases[-1]["engine"] = None
            with self.assertRaises(ValueError): named_phase(event, 0, "checkAcc")

    def test_malformed_and_out_of_range_substeps_reject(self):
        for event, step in ((None, 0), ({}, 0), (self.event(), True), (self.event(), -1), (self.event(), 1), ({"engineStep2Phases": [None]}, 0)):
            with self.assertRaises(ValueError): named_phase(event, step, "checkAcc")

    def test_signed_zero_survives_json_numeric_value(self):
        result = decoded_bits([0], ["8000000000000000"], 1)
        self.assertEqual(math.copysign(1, result[0]), -1)

    def test_bad_bits_nonfinite_and_mismatch_reject(self):
        for values, bits in (([True], ["0000000000000000"]), ([math.inf], ["7ff0000000000000"]), ([0], ["7ff8000000000000"]), ([1], ["0000000000000000"]), ([0], ["0"]), ([], [])):
            with self.assertRaises(ValueError): decoded_bits(values, bits, 1)
