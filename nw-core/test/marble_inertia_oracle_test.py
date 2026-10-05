import copy
import unittest
from types import SimpleNamespace

from marble_inertia_oracle import compare_event


class InertiaCaptureTests(unittest.TestCase):
    def setUp(self):
        self.calls = []

        def routine(result, inertia, vector):
            self.calls.append((list(inertia), list(vector)))
            for i in range(6):
                result[i] = vector[i]

        self.library = SimpleNamespace(mju_mulInertVec=routine)
        trace = [0.0] * 72
        trace[36:42] = trace[42:48] = [1, 2, 3, 4, 5, 6]
        trace[48:54] = [7, 8, 9, 10, 11, 12]
        self.event = {"rneTraces": [trace], "engineStep1Phases": [[{
            "phase": "probe_rneBias", "engine": {
                "model": {"body_parentid": [0, 0]},
                "arrays": {"qvel": [], "cinert": [0]*10 + list(range(10)),
                           "cvel": [0]*6 + [7, 8, 9, 10, 11, 12]}}}]]}

    def test_body_offsets_and_operands(self):
        rows = list(compare_event(self.event, self.library))
        self.assertEqual([r["differences"] for r in rows], [[], []])
        self.assertEqual(self.calls, [(list(range(10)), [1, 2, 3, 4, 5, 6]),
                                      (list(range(10)), [7, 8, 9, 10, 11, 12])])

    def test_malformed_dimensions_rejected_before_native_call(self):
        event = copy.deepcopy(self.event)
        event["rneTraces"][0].pop()
        with self.assertRaisesRegex(ValueError, "dimensions"):
            list(compare_event(event, self.library))
        self.assertEqual(self.calls, [])

    def test_missing_checkpoint_rejected(self):
        self.event["engineStep1Phases"] = [[]]
        with self.assertRaisesRegex(ValueError, "checkpoint"):
            list(compare_event(self.event, self.library))

    def test_nonfinite_rejected(self):
        self.event["rneTraces"][0][36] = float("nan")
        with self.assertRaisesRegex(ValueError, "non-finite"):
            list(compare_event(self.event, self.library))
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
