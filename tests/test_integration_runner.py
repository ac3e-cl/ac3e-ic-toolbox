"""The runner discovers tests, keeps going after failures and returns their status."""
import csv
import json
import os
from pathlib import Path
import subprocess
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class IntegrationRunner(unittest.TestCase):
    def test_repository_long_suite_selects_only_retained_templates(self):
        exclusions = json.loads((ROOT / 'tests/exclusions.json').read_text())
        names = {'pdk/librelane-template-ihp.sh', 'pdk/librelane-template-gf.sh'}
        sky = 'pdk/librelane-template-sky.sh'
        self.assertEqual(set(exclusions['long_running']), names | {sky})
        bodies = {name: 'exit 0\n' for name in names}
        bodies[sky] = 'exit 89\n'
        result, rows = self.run_fixture(bodies,
                                        exclusions=exclusions, full=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({row['test'] for row in rows if row['status'] == 'PASS'}, names)
        self.assertEqual([row['status'] for row in rows if row['test'] == sky], ['EXCLUDED'])

    def test_sky_tests_are_preserved_and_excluded_without_execution(self):
        exclusions = json.loads((ROOT / 'tests/exclusions.json').read_text())
        names = ('pdk/ngspice-sky130-mosfet.sh', 'pdk/librelane-template-sky.sh',
                 'pdk/librelane-smoke.sh')
        for path in ('pdk/ngspice-sky130-mosfet.sh', 'pdk/librelane-template-sky.sh',
                     'data/sky130_nmos_op.spice', 'pdk/librelane-smoke.sh'):
            with self.subTest(path=path):
                self.assertTrue((ROOT / 'tests' / path).is_file())
        bodies = {name: 'exit 89\n' for name in names}
        result, rows = self.run_fixture(bodies, exclusions=exclusions)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(rows), len(names))
        self.assertTrue(all(row['status'] == 'EXCLUDED' for row in rows))
        for name in names:
            self.assertIn('temporarily', exclusions['tests'][name].lower())
        self.assertIn('    sky)', (ROOT / 'tests/helpers/librelane-template-test.sh').read_text())
        for path in ('inventory/tools.sh', 'pdk/pdk-environment.sh'):
            with self.subTest(path=path):
                self.assertNotIn('sky', (ROOT / 'tests' / path).read_text().lower())
        inventory = (ROOT / 'tests/inventory/tools.sh').read_text()
        self.assertIn('gf180mcuD/libs.tech/ngspice/sm141064.ngspice', inventory)

    def run_fixture(self, bodies, timeout: str | None = '5', exclusions=None, trace_timeout=False, full=False):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = Path(tmp)
            runner = root / 'run_all.sh'
            runner.write_text((ROOT / 'tests/run_all.sh').read_text())
            (root / 'test_all_full.sh').write_text((ROOT / 'tests/test_all_full.sh').read_text())
            if exclusions is not None:
                (root / 'exclusions.json').write_text(json.dumps(exclusions))
            for category in ('analog', 'digital', 'gui', 'inventory', 'pdk'):
                (root / category).mkdir()
            for name, body in bodies.items():
                (root / name).write_text('#!/usr/bin/env bash\n' + body)
            env = dict(os.environ)
            if timeout is None:
                env.pop('TEST_TIMEOUT', None)
            else:
                env['TEST_TIMEOUT'] = timeout
            if trace_timeout:
                binary = root / 'bin'
                binary.mkdir()
                proxy = binary / 'timeout'
                proxy.write_text('#!/usr/bin/env bash\nprintf "Selected timeout: %s\\n" "$2"\nexec "$REAL_TIMEOUT" "$@"\n')
                proxy.chmod(0o755)
                real_timeout = shutil.which('timeout')
                assert real_timeout is not None
                env['REAL_TIMEOUT'] = real_timeout
                env['PATH'] = str(binary) + os.pathsep + env['PATH']
            result = subprocess.run(['bash', str(root / 'test_all_full.sh' if full else runner)],
                                    env=env, capture_output=True, text=True)
            report = root / ('run/full/summary.tsv' if full else 'run/summary.tsv')
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

    def test_long_tests_are_excluded_normally_and_selected_by_full_runner(self):
        bodies = {'pdk/librelane-template-ihp.sh': 'exit 0\n',
                  'pdk/quick.sh': 'exit 9\n'}
        exclusions = {'long_running': {'pdk/librelane-template-ihp.sh': 'Long flow'}}
        result, rows = self.run_fixture(bodies, exclusions=exclusions)
        self.assertEqual([r['status'] for r in rows], ['EXCLUDED', 'FAIL'])
        result, rows = self.run_fixture(bodies, exclusions=exclusions, full=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([r['test'] for r in rows], ['pdk/librelane-template-ihp.sh'])
        self.assertEqual(rows[0]['status'], 'PASS')

    def test_success_and_timeout(self):
        result, rows = self.run_fixture({'pdk/a.sh': 'exit 0\n'})
        self.assertEqual(result.returncode, 0)
        self.assertEqual(rows[0]['status'], 'PASS')
        result, rows = self.run_fixture({'gui/a.sh': 'sleep 2\n'}, timeout='0.1')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(rows[0]['status'], 'FAIL')
        self.assertIn('Exit status: 124', result.stderr)

    def test_full_templates_have_longer_default_but_global_override_wins(self):
        bodies = {'pdk/librelane-template-ihp.sh': 'exit 7\n'}
        result, _ = self.run_fixture(bodies, timeout=None, trace_timeout=True)
        self.assertIn('Selected timeout: 14400', result.stderr)
        result, _ = self.run_fixture(bodies, timeout='7', trace_timeout=True)
        self.assertIn('Selected timeout: 7', result.stderr)

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
