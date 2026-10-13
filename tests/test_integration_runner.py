"""The runner discovers tests, keeps going after failures and returns their status."""
import csv
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IntegrationRunner(unittest.TestCase):
    def run_fixture(self, bodies, timeout='5', exclusions=None):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = Path(tmp)
            runner = root / 'run_all.sh'
            runner.write_text((ROOT / 'tests/run_all.sh').read_text())
            if exclusions is not None:
                (root / 'exclusions.json').write_text(json.dumps(exclusions))
            for category in ('analog', 'digital', 'gui', 'inventory', 'pdk'):
                (root / category).mkdir()
            for name, body in bodies.items():
                (root / name).write_text('#!/usr/bin/env bash\n' + body)
            env = dict(os.environ, TEST_TIMEOUT=timeout)
            result = subprocess.run(['bash', str(runner)],
                                    env=env, capture_output=True, text=True)
            report = root / 'run/summary.tsv'
            rows = []
            if report.exists():
                with report.open() as stream:
                    rows = list(csv.DictReader(stream, delimiter='\t'))
            return result, rows

    def test_failure_does_not_stop_later_tests(self):
        result, rows = self.run_fixture({'analog/a.sh': 'exit 7\n',
                                         'digital/b.sh': 'exit 0\n'})
        self.assertEqual(result.returncode, 1)
        self.assertEqual([r['status'] for r in rows], ['FAIL', 'PASS'])
        self.assertIn('1 passed, 1 failed, 0 excluded, 2 total', result.stdout)
        self.assertIn('Exit status: 7', result.stderr)

    def test_success_and_timeout(self):
        result, rows = self.run_fixture({'pdk/a.sh': 'exit 0\n'})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(rows[0]['status'], 'PASS')
        result, rows = self.run_fixture({'gui/a.sh': 'sleep 2\n'}, timeout='0.1')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(rows[0]['status'], 'FAIL')
        self.assertIn('Exit status: 124', result.stderr)

    def test_no_tests_is_failure(self):
        result, rows = self.run_fixture({})
        self.assertEqual(result.returncode, 1)
        self.assertFalse(rows)

    def test_explicit_exclusions_are_not_executed_or_counted_as_passes(self):
        result, rows = self.run_fixture(
            {'analog/a.sh': 'exit 9\n', 'digital/b.sh': 'exit 0\n'},
            exclusions={'tests': {'analog/a.sh': 'Excluded by user'},
                        'manifest': {'XYCE_NAME': 'Not installed'}})
        self.assertEqual(result.returncode, 0)
        self.assertEqual([r['status'] for r in rows], ['EXCLUDED', 'PASS'])
        self.assertIn('1 passed, 0 failed, 1 excluded, 2 total', result.stdout)
        self.assertIn('Inventory exclusion: XYCE_NAME', result.stdout)
        self.assertNotIn('Exit status: 9', result.stderr)
