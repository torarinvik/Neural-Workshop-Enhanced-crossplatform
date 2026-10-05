"""Ensure evidence audit fails closed and never turns diagnostics into approval."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import marble_visual_evidence_audit as audit


class EvidenceAuditTest(unittest.TestCase):
    def test_current_dark_tilt_and_restart_pairs_are_in_inventory(self):
        self.assertIn((
            'marble-current-pair-20261004/dark-tilt/source-r16-seed17-east30',
            'marble-current-pair-20261004/dark-tilt/browser-r16-seed17-east30',
        ), audit.PAIRS)
        self.assertIn((
            'marble-current-pair-20261004/dark-tilt/source-r16-seed17-east30-restart',
            'marble-current-pair-20261004/dark-tilt/browser-r16-seed17-east30-restart',
        ), audit.PAIRS)
        self.assertIn((
            'marble-current-pair-20261004/dpr1-light-tilt/source-r16-seed17-east30',
            'marble-current-pair-20261004/dpr1-light-tilt/browser-r16-seed17-east30',
        ), audit.PAIRS)
        self.assertIn((
            'marble-current-pair-20261004/dpr1-dark-tilt/source-r16-seed17-east30',
            'marble-current-pair-20261004/dpr1-dark-tilt/browser-r16-seed17-east30',
        ), audit.PAIRS)
        self.assertIn((
            'mm-clearance-partial-loss-current-20261005-source',
            'mm-clearance-partial-loss-current-20261005-browser',
        ), audit.PAIRS)
        self.assertIn((
            'mm-clearance-dpr1-dark-current-20261005-source',
            'mm-clearance-dpr1-dark-current-20261005-browser',
        ), audit.PAIRS)
        self.assertIn((
            'mm-clearance-wide-dpr1-dark-current-20261005-source',
            'mm-clearance-wide-dpr1-dark-current-20261005-browser',
        ), audit.PAIRS)
        self.assertIn((
            'mm-clearance-wide-dpr1-light-current-20261005-source',
            'mm-clearance-wide-dpr1-light-current-20261005-browser',
        ), audit.PAIRS)
        self.assertIn((
            'mm-clearance-ready-wide-dpr1-light-current-20261005-source',
            'mm-clearance-ready-wide-dpr1-light-current-20261005-browser',
        ), audit.PAIRS)
        self.assertIn((
            'mm-clearance-wide-dpr1-light-physical-win-trace-20261005-source',
            'mm-clearance-wide-dpr1-light-physical-win-trace-20261005-browser',
        ), audit.PAIRS)

    @staticmethod
    def create_pair_artifacts(root, reference, candidate):
        root = Path(root)
        candidate_metadata = candidate.removesuffix('-framebuffer')
        for name in (f'{reference}.png', f'{candidate}.png',
                     f'{candidate_metadata}.json'):
            artifact = root / name
            artifact.parent.mkdir(parents=True, exist_ok=True)
            artifact.write_bytes(b'fixture')
        reference_metadata = root / f'{reference}.json'
        reference_metadata.parent.mkdir(parents=True, exist_ok=True)
        reference_metadata.write_text(json.dumps({
            'sceneState': {'phase': 'ready'}, 'terminalFixture': 'none',
            'theme': 'light', 'dpr': 1, 'rung': 1,
            'image': {'dimensions': [800, 600]},
        }))

    @classmethod
    def create_artifacts(cls, root):
        for reference, candidate in audit.PAIRS:
            cls.create_pair_artifacts(root, reference, candidate)

    def check_rejected(self, response):
        with tempfile.TemporaryDirectory() as root:
            self.create_artifacts(root)
            output = io.StringIO()
            with patch('sys.argv', ['audit', '--artifacts', root]), \
                    patch.object(audit.subprocess, 'run', return_value=response), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(audit.main(), 1)
            report = json.loads(output.getvalue())
            self.assertEqual(len(report['failures']), len(audit.PAIRS))
            self.assertFalse(report['accepted'])
            self.assertEqual(report['pairs'], [])

    def test_missing_artifacts_are_reported_before_comparison(self):
        with tempfile.TemporaryDirectory() as root:
            output = io.StringIO()
            with patch('sys.argv', ['audit', '--artifacts', root]), \
                    patch.object(audit.subprocess, 'run') as run, \
                    contextlib.redirect_stdout(output):
                self.assertEqual(audit.main(), 1)
            report = json.loads(output.getvalue())
            self.assertEqual(len(report['failures']), len(audit.PAIRS))
            self.assertIn('missing artifact(s):', report['failures'][0]['error'])
            run.assert_not_called()

    def test_missing_or_failed_pair(self):
        self.check_rejected(subprocess.CompletedProcess([], 1, '', 'missing PNG'))

    def test_artifacts_can_be_resolved_from_multiple_roots(self):
        comparator_output = json.dumps({
            'result': 'diagnostic-only', 'failures': [], 'metrics': {},
            'regions': {'stage': {}}, 'candidateReadback': {},
        })
        with tempfile.TemporaryDirectory() as first, \
                tempfile.TemporaryDirectory() as second:
            for index, (reference, candidate) in enumerate(audit.PAIRS):
                self.create_pair_artifacts(
                    first if index % 2 == 0 else second, reference, candidate)
            output = io.StringIO()
            argv = ['audit', '--artifacts', first, '--artifacts', second]
            with patch('sys.argv', argv), \
                    patch.object(audit.subprocess, 'run', return_value=
                                 subprocess.CompletedProcess([], 0, comparator_output, '')), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(audit.main(), 0)
            report = json.loads(output.getvalue())
            self.assertEqual(len(report['pairs']), len(audit.PAIRS))
            self.assertEqual(report['failures'], [])
            self.assertFalse(report['accepted'])

    def test_output_receipt_is_persisted(self):
        comparator_output = json.dumps({
            'result': 'diagnostic-only', 'failures': [], 'metrics': {},
            'regions': {'stage': {}}, 'candidateReadback': {},
        })
        with tempfile.TemporaryDirectory() as root:
            self.create_artifacts(root)
            receipt = Path(root) / 'nested' / 'audit.json'
            output = io.StringIO()
            argv = ['audit', '--artifacts', root, '--output', str(receipt)]
            with patch('sys.argv', argv), \
                    patch.object(audit.subprocess, 'run', return_value=
                                 subprocess.CompletedProcess([], 0, comparator_output, '')), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(audit.main(), 0)
            printed = json.loads(output.getvalue())
            persisted = json.loads(receipt.read_text())
            self.assertEqual(persisted, printed)
            self.assertFalse(persisted['accepted'])
            self.assertEqual(len(persisted['pairs']), len(audit.PAIRS))

    def test_accepted_label_cannot_substitute_for_diagnostic(self):
        self.check_rejected(subprocess.CompletedProcess([], 0,
            json.dumps({'result': 'accepted', 'failures': []}), ''))

    def test_malformed_receipt(self):
        self.check_rejected(subprocess.CompletedProcess([], 0, '{bad', ''))

    def test_non_object_receipts(self):
        for value in (None, [], [1], True, 2, "diagnostic-only"):
            with self.subTest(value=value):
                self.check_rejected(subprocess.CompletedProcess([], 0, json.dumps(value), ''))


if __name__ == '__main__':
    unittest.main()
