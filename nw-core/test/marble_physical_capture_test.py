import unittest
from types import SimpleNamespace
from marble_source_capture import (require_physical_terminal, parse_capture_trace,
                                   trace_time_limit_seconds,
                                   validate_terminal_capture)


class PhysicalCaptureTest(unittest.TestCase):
    def test_real_replay_supports_all_rungs_without_widening_forced_fixtures(self):
        for rung in range(1, 17):
            validate_terminal_capture(rung, True, True)
            validate_terminal_capture(rung, True, False)
        validate_terminal_capture(1, False, False)
        for rung, scripted in ((2, False), (16, False), (1, True)):
            with self.assertRaises(SystemExit):
                validate_terminal_capture(rung, False, scripted)

    def test_trace_discards_poses(self):
        trace = {'rung': 1, 'runSeed': 17, 'timeLimitMs': 120000, 'events': [
            {'kind': 'frame', 'dt': 1/60, 'held': ['E'], 'state': {'fake': 'pose'}},
            {'kind': 'level', 'state': {'fake': 'pose'}}]}
        actions = parse_capture_trace(trace, 1, 17)
        self.assertEqual(actions, [{'kind': 'frame', 'dt': 1/60, 'held': ['E']},
                                   {'kind': 'level'}])
        self.assertEqual(trace_time_limit_seconds(trace), 120.0)
        with self.assertRaises(SystemExit):
            parse_capture_trace(trace, 1, 18)

    def test_trace_limit_defaults_to_board_and_rejects_invalid_values(self):
        self.assertEqual(trace_time_limit_seconds({}), 0.0)
        for invalid in (True, 1, 14999, 120001, 15.0, "120000"):
            with self.subTest(invalid=invalid), self.assertRaises(SystemExit):
                trace_time_limit_seconds({'timeLimitMs': invalid})

    def test_trace_invalid_inputs(self):
        for event in ({'kind': 'frame', 'dt': float('nan'), 'held': []},
                      {'kind': 'frame', 'dt': 1, 'held': []},
                      {'kind': 'frame', 'dt': 1/60, 'held': ['E', 'E']},
                      {'kind': 'frame', 'dt': 1/60, 'held': ['Q']},
                      {'kind': 'teleport'}):
            with self.assertRaises(SystemExit):
                parse_capture_trace({'rung': 1, 'runSeed': 17, 'events': [event]}, 1, 17)
        with self.assertRaisesRegex(SystemExit, 'timeLimitMs'):
            parse_capture_trace({'rung': 1, 'runSeed': 17, 'timeLimitMs': 1,
                                 'events': [{'kind': 'level'}]}, 1, 17)

    def test_real_settled_phase_required(self):
        for outcome in ('won', 'lost', 'done'):
            phase = 'won' if outcome == 'done' else outcome
            task = SimpleNamespace(phase=phase, sim=SimpleNamespace(settled=True))
            require_physical_terminal(task, outcome)
            task.sim.settled = False
            with self.assertRaises(SystemExit):
                require_physical_terminal(task, outcome)
            task.sim = None
            with self.assertRaises(SystemExit):
                require_physical_terminal(task, outcome)

    def test_wrong_phase_rejected(self):
        task = SimpleNamespace(phase='rolling', sim=SimpleNamespace(settled=True))
        with self.assertRaises(SystemExit):
            require_physical_terminal(task, 'won')


if __name__ == '__main__':
    unittest.main()
