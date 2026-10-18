"""Exercise the real build wrapper with a subprocess Docker executable."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildOutputTests(unittest.TestCase):
    def test_progress_deduplicates_and_bounds_stage_headers(self):
        header = '#12 [builder 1/1] RUN ' + 'package ' * 100 + '\n'
        result = subprocess.run(
            ['awk', '-v', 'verbose=false', '-f', str(ROOT / 'build/build-progress.awk')],
            input=header * 3 + '#12 DONE 1.0s\n', text=True, capture_output=True)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout.splitlines()), 2)
        self.assertLessEqual(len(result.stdout.splitlines()[0]), 160)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'build').mkdir()
        for source in (ROOT / 'build').glob('build*'):
            if source.is_file():
                shutil.copy2(source, self.root / 'build' / source.name)
        (self.root / 'Dockerfile').write_text('FROM scratch AS final\n')
        (self.root / 'manifest.json').write_text(json.dumps({
            'schemaVersion': 1, 'release': {'version': '1.2.3'},
            'image': {'registry': '', 'namespace': 'test', 'name': 'image'},
            'build': {'target': 'final', 'arguments': {}}}))
        docker = self.root / 'docker'
        docker.write_text('''#!/usr/bin/env bash
if [[ "$1" == image ]]; then echo inspected; exit "${INSPECT_STATUS:-0}"; fi
printf '%s\\n' "$*" > "$ARGS_FILE"
printf '#1 [final 1/1] RUN compile\\n' >&2
for ((i=0;i<150;i++)); do printf '#1 0.1 compiler-spam-%s\\n' "$i"; done
if [[ "${STATUS:-0}" != 0 ]]; then printf '#1 ERROR: compile failed\\nERROR: build failed\\n' >&2; fi
exit "${STATUS:-0}"
''')
        docker.chmod(0o755)

    def run_build(self, **overrides):
        env = os.environ.copy()
        for key in ('CHECK_ONLY', 'BUILD_VERBOSE', 'BUILDKIT_PROGRESS', 'STATUS',
                    'BUILD_MAX_PARALLELISM', 'BUILD_BUILDER'):
            env.pop(key, None)
        env.update(PATH=str(self.root) + os.pathsep + env['PATH'],
                   ARGS_FILE=str(self.root / 'args'))
        env.update(overrides)
        return subprocess.run(['bash', str(self.root / 'build/build-stage.sh'), 'final'],
                              env=env, text=True, capture_output=True)

    def log(self, result):
        output = result.stdout + result.stderr
        line = next(line for line in output.splitlines() if line.startswith('Build log: '))
        return Path(line.removeprefix('Build log: '))

    def test_failure_keeps_status_and_prints_bounded_tail(self):
        result = self.run_build(STATUS='23')
        self.assertEqual(result.returncode, 23)
        self.assertIn('ERROR: build failed', result.stderr)
        self.assertIn('compiler-spam-149', result.stderr)
        self.assertNotIn('compiler-spam-0\n', result.stdout + result.stderr)
        self.assertLessEqual(len(result.stderr.splitlines()), 43)
        self.assertNotIn('inspected', result.stdout)
        self.assertIn('compiler-spam-0\n', self.log(result).read_text())

    def test_verbose_streams_full_output(self):
        result = self.run_build(BUILD_VERBOSE='1')
        self.assertEqual(result.returncode, 0)
        self.assertIn('compiler-spam-0\n', result.stdout)
        self.assertIn('compiler-spam-149', self.log(result).read_text())

    def test_checks_keep_all_diagnostics_and_skip_inspection(self):
        result = self.run_build(CHECK_ONLY='1', STATUS='7')
        self.assertEqual(result.returncode, 7)
        self.assertIn('--check', (self.root / 'args').read_text())
        self.assertIn('compiler-spam-0\n', result.stdout)
        self.assertNotIn('inspected', result.stdout)

    def test_successful_check_skips_inspection(self):
        result = self.run_build(CHECK_ONLY='yes')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('inspected', result.stdout)

    def test_explicit_progress_mode_streams_native_output(self):
        result = self.run_build(BUILDKIT_PROGRESS='rawjson')
        self.assertEqual(result.returncode, 0)
        self.assertIn('--progress rawjson', (self.root / 'args').read_text())
        self.assertIn('compiler-spam-0\n', result.stdout)

    def test_inspection_failure_status_is_preserved(self):
        result = self.run_build(INSPECT_STATUS='19')
        self.assertEqual(result.returncode, 19)

    def test_false_verbose_remains_quiet(self):
        result = self.run_build(BUILD_VERBOSE='false')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('compiler-spam', result.stdout + result.stderr)

    def test_default_shows_stage_without_compiler_spam_and_saves_full_log(self):
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('[final 1/1] RUN compile', result.stdout)
        self.assertNotIn('compiler-spam', result.stdout + result.stderr)
        self.assertIn('compiler-spam-149', self.log(result).read_text())
        self.assertIn('_build_logs', str(self.log(result)))


if __name__ == '__main__':
    unittest.main()
