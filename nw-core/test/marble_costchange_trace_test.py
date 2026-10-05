import copy
import math
import os
import unittest

from marble_costchange_trace import (OriginalCostPrimitives,capture_cost,
    compare,decode_cost,existing_diagnostic_difference)


def document(*,restored=False,guard=False):
    old=[1.,2.] if guard else [0.,0.]
    proposed=[0.,0.] if guard else [1.,2.]
    matrix=[2.,0.,0.,2.]
    residual=[0.,0.] if guard else ([2.,4.] if restored else [-2.,-4.])
    delta=[a-b for a,b in zip(proposed,old)]
    quadratic=10.;dot=sum(a*b for a,b in zip(delta,residual))
    before=.5*quadratic+dot;restored=before>1e-10
    final=0. if restored else before;retained=old if restored else proposed
    qcqp=[1,0,0,0,0,0,3,0 if guard else 2,4 if guard else 7,
          -1 if guard else 0,0,int(restored),final,0 if guard else 3]
    qcqp+=[1.,1.]+matrix+residual+old+residual
    if not guard:qcqp+=proposed+proposed
    qcqp+=retained
    cost=[1,0,0,0,0,0,2,7,int(restored),quadratic,dot,before,final]
    cost+=matrix+old+proposed+residual+delta+retained
    return dict(qcqpTraceSchema=1,qcqpTraceCalls=1,qcqpTraceOverflow=False,
        qcqpTraceInvalid=False,qcqpTrace=qcqp,costChangeSchema=1,
        costChangeCalls=1,costChangeOverflow=False,costChangeInvalid=False,costChangeTrace=cost)


class CostDecoderTests(unittest.TestCase):
    def test_assigned_scalars_and_all_operand_force_boundaries_are_retained(self):
        row=capture_cost(document())[0]
        self.assertEqual(row["quadratic"],10.)
        self.assertEqual(row["dot"],-10.)
        self.assertEqual(row["beforeChange"],-5.)
        self.assertEqual(row["delta"],[1.,2.])
        self.assertEqual(row["beforeForce"],row["finalForce"])

    def test_actual_restoration_and_normal_guard_own_the_final_force(self):
        for kwargs in (dict(restored=True),dict(guard=True)):
            row=capture_cost(document(**kwargs))[0]
            self.assertTrue(row["restored"])
            self.assertGreater(row["beforeChange"],1e-10)
            self.assertEqual(row["finalChange"],0.)
            self.assertEqual(row["oldForce"],row["finalForce"])

    def test_every_truncation_and_trailing_value_is_rejected(self):
        values=document()["costChangeTrace"]
        for end in range(len(values)):
            with self.subTest(end=end),self.assertRaises(ValueError):decode_cost(values[:end],1)
        with self.assertRaises(ValueError):decode_cost(values+[0.],1)

    def test_whole_finite_packet_count_and_capacity_checked(self):
        for value in (True,math.nan,math.inf,"1",None):
            values=document()["costChangeTrace"];values[-1]=value
            with self.assertRaises(ValueError):decode_cost(values,1)
        for count in (True,-1,1000001,2,None):
            with self.assertRaises(ValueError):decode_cost(document()["costChangeTrace"],count)
        with self.assertRaises(ValueError):decode_cost([0.]*300001,0)
        self.assertEqual(decode_cost([],0),[])

    def test_schema_masks_dimensions_ordinal_and_branch_are_not_inferred(self):
        for index,value in ((0,2),(1,1),(2,-2),(3,-1),(4,-1),(5,-1),
                (6,1),(6,4),(6,6),(7,3),(8,1),(12,0),(-1,0)):
            values=document()["costChangeTrace"];values[index]=value
            with self.subTest(index=index),self.assertRaises(ValueError):decode_cost(values,1)

    def test_cost_delta_and_owners_must_retain_actual_boundary(self):
        values=document()["costChangeTrace"];values[-4]=0
        with self.assertRaises(ValueError):decode_cost(values,1)
        for index in (2,3,4,5,13):
            doc=document();doc["costChangeTrace"][index]+=1
            with self.subTest(index=index),self.assertRaises(ValueError):capture_cost(doc)
        doc=document();doc["costChangeTrace"][19]+=1
        doc["costChangeTrace"][23]+=1
        doc["costChangeTrace"][25]+=1
        # Structurally valid forces/delta, but not the actual outer force.
        with self.assertRaises(ValueError):capture_cost(doc)

    def test_metadata_must_be_explicit_and_nonoverflowed(self):
        for field,value in (("costChangeSchema",True),("costChangeOverflow",None),
                ("costChangeInvalid",True),("costChangeCalls",True)):
            doc=document();doc[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):capture_cost(doc)

    def test_decoder_does_not_impose_a_fused_or_rounded_recomposition(self):
        values=document()["costChangeTrace"];values[9]=11
        # Structural reading preserves assigned result, never substitutes a model.
        self.assertEqual(decode_cost(values,1)[0]["quadratic"],11)

    def test_existing_diagnostics_must_stay_exact_not_only_frame_physics(self):
        control=dict(events=[dict(newtonTraces=[document()])])
        candidate=copy.deepcopy(control)
        candidate["events"][0]["newtonTraces"][0]["newRecorder"]=[]
        self.assertIsNone(existing_diagnostic_difference(control,candidate))
        candidate["events"][0]["newtonTraces"][0]["qcqpTraceCalls"]=2
        self.assertEqual(existing_diagnostic_difference(control,candidate)["field"],"qcqpTraceCalls")
        self.assertEqual(existing_diagnostic_difference(control,dict(events=[])),dict(field="event count"))

    def test_invalid_primitive_arrays_are_rejected_before_native_callback(self):
        original=OriginalCostPrimitives.__new__(OriginalCostPrimitives)
        def forbidden(*args):raise AssertionError("must not call native")
        original.mju_mulVecMatVec=original.mju_dot=forbidden
        for delta,matrix,residual in (([1.], [1.], [1.]),([1.,2.],[1.],[1.,2.]),
                ([1.,2.],[0.]*4,[True,2.]),([math.inf,0.],[0.]*4,[1.,2.])):
            with self.assertRaises(ValueError):original.evaluate(delta,matrix,residual)

    def test_inventory_allows_only_named_additive_cost_metadata(self):
        control=dict(events=[dict(newtonTraces=[dict(traceKeys=["qcqpTrace"],qcqpTrace=[1.])])])
        candidate=copy.deepcopy(control)
        t=candidate["events"][0]["newtonTraces"][0]
        t["traceKeys"]=["costChangeTrace","qcqpTrace"]
        t["costChangeTrace"]=[]
        self.assertIsNone(existing_diagnostic_difference(control,candidate))
        for keys in ([],["costChangeTrace"],["qcqpTrace","surprise"],
                     ["qcqpTrace","qcqpTrace"],["qcqpTrace","costChangeTrace"],[1]):
            t["traceKeys"]=keys
            with self.subTest(keys=keys):
                self.assertEqual(existing_diagnostic_difference(control,candidate)["field"],"traceKeys")
        t["traceKeys"]=["costChangeTrace","qcqpTrace"]
        del t["qcqpTrace"]
        self.assertEqual(existing_diagnostic_difference(control,candidate)["field"],"qcqpTrace")

    def test_later_invalid_capture_is_rejected_before_any_native_call(self):
        first=document();second=document();second["costChangeCalls"]=2
        trace=dict(events=[dict(newtonTraces=[first,second])])
        class ForbiddenOriginal:
            def evaluate(self,*args):raise AssertionError("must validate every capture first")
        with self.assertRaises(ValueError):compare(trace,ForbiddenOriginal())


@unittest.skipUnless(os.environ.get("NW_MUJOCO_REFERENCE_LIBRARY"),"requires exact original wheel")
class DirectOriginalCostPrimitiveTests(unittest.TestCase):
    def test_actual_public_quadratic_and_dot_on_all_tangent_dimensions(self):
        original=OriginalCostPrimitives(os.environ["NW_MUJOCO_REFERENCE_LIBRARY"])
        for n in (2,3,5):
            delta=[float(i+1) for i in range(n)]
            matrix=[float(i==j) for i in range(n) for j in range(n)]
            expected=sum(v*v for v in delta)
            self.assertEqual(original.evaluate(delta,matrix,delta),dict(quadratic=expected,dot=expected))


if __name__=="__main__":unittest.main()
