import copy
import math
import unittest
from unittest.mock import patch

from marble_qcqp_kernel_trace import capture_kernel, comparison_scope, decode_kernel
from marble_qcqp_trace import capture_qcqp
from marble_qcqp_trace_test import document, record


def contact(active=False, ordinal=0):
    c=capture_qcqp(document(record(active=int(active))))[0]
    c["ordinal"]=ordinal
    return c


def step(reason=1, ordinal=0, parent=0, iteration=0, before=0., solved=2.):
    valid=(3,7,15,31,31)[reason]
    rank=4 if reason==0 else 5
    value=0. if reason<2 else 1.
    product=1e11 if reason==2 else 1. if reason>=3 else 0.
    derivative=-2.*product
    delta=-value/derivative if reason>=2 else 0.
    after=before+delta if reason>=3 else before
    norm=0. if reason==0 else 1.
    values=[1,ordinal,parent,iteration,5,rank,valid,reason,
            before,after,norm,value,product,derivative,delta]
    values += [1.]*25+[0.]*5+[1.]*25+[1.]*25
    if valid&4:values += [solved]*5
    if valid&8:values += [1.]*5
    return values


class KernelTraceTests(unittest.TestCase):
    def test_default_neutrality_is_not_disabled_by_arithmetic_diagnosis(self):
        trace={"events":[{}]}
        with patch("marble_qcqp_kernel_trace.validate_neutral_pair", side_effect=ValueError("not neutral")):
            with self.assertRaisesRegex(ValueError,"not neutral"):
                comparison_scope(trace,trace)

    def test_explicit_arithmetic_scope_checks_bytes_without_claiming_neutrality(self):
        trace={"events":[{}]};difference={"event":0,"field":"position"}
        with patch("marble_qcqp_kernel_trace.validate_runtime_pair") as check, \
                patch("marble_qcqp_kernel_trace.first_physics_difference",return_value=difference):
            scope=comparison_scope(trace,trace,True)
            check.assert_called_once_with(trace,trace)
        self.assertFalse(scope["claimed"])
        self.assertFalse(scope["exact"])
        self.assertEqual(scope["firstPhysicsDifference"],difference)
        with patch("marble_qcqp_kernel_trace.validate_runtime_pair",side_effect=ValueError("stale runtime")):
            with self.assertRaisesRegex(ValueError,"stale runtime"):
                comparison_scope(trace,trace,True)

    def test_value_terminal_keeps_assigned_solve_not_uninitialized_second_solve(self):
        g=decode_kernel(step(),1,[contact()])[0]
        self.assertEqual(g["steps"][0]["reason"],"value")
        self.assertNotIn("inverseSolved",g["steps"][0])
        self.assertNotIn("delta",g["steps"][0])
        self.assertEqual(g["steps"][0]["solved"],[2.]*5)

    def test_rank_terminal_does_not_copy_either_uninitialized_solve(self):
        c=contact();c["rawForce"]=[0.]*5
        s=decode_kernel(step(reason=0),1,[c])[0]["steps"][0]
        self.assertNotIn("solved",s)
        self.assertNotIn("norm",s)
        self.assertEqual(s["rank"],4)

    def test_delta_terminal_uses_second_solve_without_lambda_update(self):
        s=decode_kernel(step(reason=2),1,[contact()])[0]["steps"][0]
        self.assertEqual(s["inverseSolved"],[1.]*5)
        self.assertEqual(s["lambdaAfter"],0.)
        self.assertLess(s["delta"],1e-10)

    def test_updates_and_terminal_iteration_link_to_actual_outer_raw_return(self):
        c=contact(True)
        values=step(reason=3,solved=3.)+step(ordinal=1,iteration=1,before=.5,solved=3.)
        g=decode_kernel(values,2,[c])[0]
        self.assertEqual([s["lambdaAfter"] for s in g["steps"]],[.5,.5])
        with self.assertRaises(ValueError):decode_kernel(values,2,[contact(False)])

    def test_exact_twenty_iteration_limit_is_explicit_and_not_inferred(self):
        values=[]
        for i in range(20):
            values+=step(reason=4 if i==19 else 3,ordinal=i,iteration=i,before=.5*i,solved=3.)
        g=decode_kernel(values,20,[contact(True)])[0]
        self.assertEqual(g["steps"][-1]["reason"],"limit")
        self.assertEqual(g["steps"][-1]["lambdaAfter"],10.)
        with self.assertRaises(ValueError):decode_kernel(step(reason=4),1,[contact(True)])

    def test_multiple_parent_associations_allow_ignored_other_routes(self):
        a,b=contact(),contact(ordinal=2)
        values=step()+step(ordinal=1,parent=2)
        self.assertEqual([g["parent"] for g in decode_kernel(values,2,[a,b])],[0,2])
        with self.assertRaises(ValueError):decode_kernel(values,2,[a])

    def test_every_truncation_trailing_value_and_missing_terminal_is_rejected(self):
        values=step()
        for stop in range(len(values)):
            with self.subTest(stop=stop),self.assertRaises(ValueError):
                decode_kernel(values[:stop],1,[contact()])
        with self.assertRaises(ValueError):decode_kernel(values+[1],1,[contact()])
        with self.assertRaises(ValueError):decode_kernel(step(reason=3,solved=3.),1,[contact(True)])
        self.assertEqual(decode_kernel([],0,[]),[])
        with self.assertRaises(ValueError):decode_kernel([],0,[contact()])

    def test_ordinal_iteration_parent_and_continuation_flags_are_not_guessed(self):
        for index,value in ((0,2),(1,1),(2,1),(3,1),(4,4),(5,4),(6,31),(7,3),
                            (8,-1.),(9,1.),(12,1.),(13,1.),(14,1.)):
            values=step();values[index]=value
            with self.subTest(index=index),self.assertRaises(ValueError):
                decode_kernel(values,1,[contact()])
        with self.assertRaises(ValueError):
            decode_kernel(step()+step(ordinal=1,iteration=1),2,[contact()])

    def test_update_scalars_and_initialized_inputs_cannot_mutate_between_iterations(self):
        values=step(reason=3,solved=3.)+step(ordinal=1,iteration=1,before=.5,solved=3.)
        for index in (len(step(reason=3))+8,len(step(reason=3))+15):
            bad=values.copy();bad[index]+=1.
            with self.assertRaises(ValueError):decode_kernel(bad,2,[contact(True)])
        values=step(reason=3,solved=3.);values[14]=.25
        with self.assertRaises(ValueError):decode_kernel(values,1,[contact(True)])

    def test_whole_numeric_capacity_count_and_outer_data_are_validated(self):
        for value in (True,None,"1",math.nan,math.inf):
            v=step();v[-1]=value
            with self.assertRaises(ValueError):decode_kernel(v,1,[contact()])
        with self.assertRaises(ValueError):decode_kernel([0.]*300001,0,[])
        for calls in (True,-1,1000001,None,2):
            with self.assertRaises(ValueError):decode_kernel(step(),calls,[contact()])
        for c in (None,{},dict(contact(),route=True),dict(contact(),rawForce=[1.]*4),
                  dict(contact(),active=1),dict(contact(),matrix=[1.]*24)):
            with self.assertRaises(ValueError):decode_kernel(step(),1,[c])

    def test_schema_overflow_and_invalid_metadata_are_explicit(self):
        trace=dict(document(record(active=0)),qcqpKernelSchema=1,qcqpKernelCalls=1,
            qcqpKernelOverflow=False,qcqpKernelInvalid=False,qcqpKernelTrace=step())
        self.assertEqual(len(capture_kernel(trace)),1)
        for field,value in (("qcqpKernelSchema",True),("qcqpKernelSchema",2),
                ("qcqpKernelOverflow",0),("qcqpKernelInvalid",None),("qcqpTraceInvalid",True)):
            bad=copy.deepcopy(trace);bad[field]=value
            with self.assertRaises(ValueError):capture_kernel(bad)
