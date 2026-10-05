import hashlib
import json
import os
from pathlib import Path
import unittest

from marble_constraint_update_oracle import captured_difference
from marble_qcqp_original import OriginalQCQP5
from marble_qcqp_trace import decode_qcqp

ROOT=Path(__file__).resolve().parent


def fixture():
    return json.loads((ROOT/"fixtures"/"marble_qcqp_boundary.json").read_text())


def packed(c):
    n=c["dim"]-1
    header=[1,c["ordinal"],c["island"],c["iteration"],c["row"],c["contact"],
            c["dim"],c["route"],c["valid"],int(c["active"]),int(c["projected"]),
            int(c["restored"]),c["costChange"],c["normal"]]
    values=header+c["mu"]+c["matrix"]+c["rhs"]+c["oldForce"]+c["residual"]
    if c["valid"]&1:values+=c["rawForce"]
    if c["valid"]&2:values+=c["projectedForce"]
    values+=c["retainedForce"]
    if len(values)!=14+n*n+7*n:
        raise ValueError("fixture witness dimension differs")
    return values


class QCQPBoundaryFixtureTests(unittest.TestCase):
    def test_recorder_delta_and_exact_neutrality_are_retained(self):
        f=fixture()
        self.assertEqual(f["schema"],"neural-workshop.marble-qcqp-boundary.v1")
        self.assertEqual(f["neutrality"],dict(exact=True,events=7601))
        self.assertEqual(f["control"]["sha256"],
            "e9dd0001c861c7c577605cd36b317907f61203a9f5cbcb83c0e95df77940291a")
        self.assertEqual(f["trace"]["sha256"],
            "c382da792a8b7cb36465ce66b2c60f2f644a0b8eab26fc68a8f1dc67180589d3")
        patch=ROOT/"repro"/"marble_initialized_qcqp_boundary.patch"
        self.assertEqual(hashlib.sha256(patch.read_bytes()).hexdigest(),f["recorderPatch"]["sha256"])

    def test_local_raw_failure_is_preserved_not_misreported_as_parity(self):
        f=fixture()
        self.assertEqual(f["counts"],dict(records=134,genericCalls=114,active=96,
            inactive=18,normalGuard=2,qcqp2Calls=18,qcqp3Calls=0,rawDifferentCalls=29,
            activeDifferentCalls=0,restored=0,decomposedCalls=114,
            decomposedNonzeroDifferentCalls=0,decomposedActiveDifferentCalls=0))
        self.assertFalse(f["capturedBrowserZeroSigns"])
        c=f["firstRetainedContact"]
        self.assertEqual((c["event"],c["substep"]), (17,0))
        self.assertEqual(c["rawDifference"]["first"]["referenceBits"],"b7f79e6e17344b5a")
        self.assertEqual(c["rawDifference"]["first"]["capturedBits"],"b7f79e6e17344b5b")
        self.assertFalse(c["captured"]["restored"])
        self.assertEqual(len(c["decomposedOriginalDriver"]["steps"]),18)

    def test_every_saved_initialized_raw_witness_round_trips_the_decoder(self):
        for w in fixture()["witnesses"]+[fixture()["firstRetainedContact"]]:
            c=w["captured"]
            row=c.copy();row["ordinal"]=0
            decoded=decode_qcqp(packed(row),1)[0]
            self.assertEqual(decoded,row)
            self.assertEqual(captured_difference(w["actualOriginalQCQP"]["rawForce"],
                c["rawForce"]),w["rawDifference"])

    def test_known_first_contact_operands_match_the_qualified_v2_witness(self):
        a=json.loads((ROOT/"fixtures"/"marble_solver_residual_order_rejected.json").read_text())["nextNoSlipForceBoundary"]
        b=fixture()["firstRetainedContact"]
        for name in ("normal","mu","matrix","rhs","oldForce","residual"):
            self.assertEqual(b["captured"][name],a["qualifiedNative"][name])
            self.assertEqual(b["captured"][name],a["browser"][name])
        self.assertEqual(b["actualOriginalQCQP"],a["actualOriginalQCQP"])
        self.assertEqual(b["captured"]["retainedForce"],a["browser"]["updatedForce"])


@unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),"requires exact original wheel")
class DirectOriginalReceiptTests(unittest.TestCase):
    def test_saved_raw_outputs_and_decomposed_control_match_actual_original(self):
        original=OriginalQCQP5(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        for w in fixture()["witnesses"]+[fixture()["firstRetainedContact"]]:
            c=w["captured"];inputs=(c["matrix"],c["rhs"],c["mu"],c["normal"])
            direct=original.solve(*inputs)
            self.assertEqual(direct,w["actualOriginalQCQP"])
            model=original.decomposed(*inputs)
            self.assertEqual({k:model[k] for k in ("active","rawForce")},direct)
            if "decomposedOriginalDriver" in w:
                self.assertEqual(model,w["decomposedOriginalDriver"])
