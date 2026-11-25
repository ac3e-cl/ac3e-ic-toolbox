"""Launcher regressions for the system Bash shipped with macOS."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get('TEST_BASH', '/bin/bash')


class BashCompatibility(unittest.TestCase):
    def test_launcher_preserves_set_values_and_redacts_diagnostics(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as directory:
            config = Path(directory) / 'launcher.env'
            config.write_text('DOCKER_TAG=from-file\nSTD_CELL_LIBRARY=from-file\n')
            env = dict(os.environ, ENV_FILE=str(config), DRY_RUN='1',
                       DOCKER_REGISTRY='', DOCKER_USER='', DOCKER_IMAGE='regression',
                       DOCKER_TAG='', STD_CELL_LIBRARY='', VNC_PW='test-only-value')
            result = subprocess.run(
                [BASH, str(ROOT / 'runtime/start.sh'), 'vnc', '--print-json'],
                env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            argv = json.loads(result.stdout)
            self.assertIn('regression:', argv)
            self.assertIn('STD_CELL_LIBRARY=', argv)
            self.assertIn('VNC_PW=[REDACTED]', argv)
            self.assertNotIn('test-only-value', result.stdout)

    def test_launcher_reuses_existing_container(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as directory:
            shared = str(Path(directory))
            state = [{'Config': {'Image': 'regression:test',
                                'Labels': {'org.ac3e.ic-toolbox.mode': 'vnc',
                                           'org.ac3e.ic-toolbox.identity': f'{os.getuid()}:{os.getgid()}:home-links-v1'}},
                      'State': {'Running': False},
                      'Mounts': [{'Source': shared, 'Destination': '/home/designer/shared'}]}]
            shim = Path(directory) / 'docker'
            shim.write_text('#!/usr/bin/env python3\nimport os, sys\n'
                            'args = sys.argv[1:]\n'
                            'if args[:2] == ["container", "ls"]: print("regression")\n'
                            'elif args[:2] == ["container", "inspect"]: print(os.environ["TEST_STATE"])\n'
                            'else: print(" ".join(args))\n')
            shim.chmod(0o755)
            env = dict(os.environ, ENV_FILE=str(Path(directory) / 'absent.env'),
                       DRY_RUN='0', NO_PULL='1', SHARED_DIR=shared, DESIGNS=shared,
                       DOCKER_REGISTRY='', DOCKER_USER='', DOCKER_IMAGE='regression',
                       DOCKER_TAG='test', CONTAINER_NAME='regression',
                       TEST_STATE=json.dumps(state), PATH=directory + os.pathsep + os.environ['PATH'])
            result = subprocess.run([BASH, str(ROOT / 'runtime/start.sh'), 'vnc'],
                                    env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), 'container start regression')


if __name__ == '__main__':
    unittest.main()
