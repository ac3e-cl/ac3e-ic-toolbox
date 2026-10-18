import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
VERSION = json.loads((ROOT / 'manifest.json').read_text())['release']['version']

class Launchers(unittest.TestCase):
    def launch(self, mode='shell', *args, **env):
        clean = {k: v for k, v in os.environ.items() if k not in ('DESIGNS', 'SHARED_DIR', 'DISPLAY', 'DOCKER_USER', 'DOCKER_REGISTRY')}
        clean.update(DRY_RUN='1', ENV_FILE='/dev/null')
        clean.update(env)
        return subprocess.run(['bash', str(ROOT / f'start_{mode}.sh'), '--print-json', *args], env=clean, text=True, capture_output=True)

    def test_shell_literal_argv_and_safe_defaults(self):
        result = self.launch('shell', 'printf', 'a b', '*')
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = json.loads(result.stdout)
        self.assertEqual(argv[-4:], ['--shell', 'printf', 'a b', '*'])
        self.assertIn(f'isaiash/ac3e-ic-toolbox:{VERSION}', argv)
        self.assertIn(f'type=bind,source={ROOT}/shared,target=/home/designer/shared', argv)
        self.assertIn(f'type=bind,source={ROOT}/tests,target=/home/designer/tests', argv)
        self.assertFalse(any('DISPLAY' in a or 'privileged' in a or 'net=host' in a for a in argv))

    def test_arbitrary_uid_gets_private_home_and_literal_bootstrap(self):
        result = self.launch('shell', 'printf', 'a b', '*', CONTAINER_USER='12345', CONTAINER_GROUP='23456')
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = json.loads(result.stdout)
        self.assertIn('12345:23456', argv)
        self.assertIn('HOME=/tmp/ac3e-ic-toolbox-home', argv)
        self.assertIn('/tmp/ac3e-ic-toolbox-home:rw,nosuid,nodev,mode=0700,uid=12345,gid=23456', argv)
        self.assertIn('--entrypoint', argv)
        self.assertEqual(argv[-4:], ['--shell', 'printf', 'a b', '*'])
        self.assertNotIn('chown', ' '.join(argv))

    def test_test_mode_has_separate_mounts_and_no_terminal(self):
        result = subprocess.run(
            ['bash', str(ROOT / 'runtime/start.sh'), 'test', '--print-json'],
            env=dict(os.environ, DRY_RUN='1', ENV_FILE='/dev/null'),
            text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = json.loads(result.stdout)
        self.assertIn('--rm', argv)
        self.assertNotIn('-it', argv)
        self.assertIn(f'type=bind,source={ROOT}/tests,target=/home/designer/tests', argv)
        self.assertEqual(argv[-3:], ['--shell', 'bash', '/home/designer/tests/run_all.sh'])

    def test_desktop_and_library_settings_are_forwarded(self):
        result = self.launch('vnc', VNC_PW='fixture-only', VNC_RESOLUTION='1024x768', STD_CELL_LIBRARY='gf180mcu_fd_sc_mcu9t5v0')
        argv = json.loads(result.stdout)
        self.assertIn('VNC_PW=[REDACTED]', argv)
        self.assertIn('VNC_RESOLUTION=1024x768', argv)
        self.assertIn('STD_CELL_LIBRARY=gf180mcu_fd_sc_mcu9t5v0', argv)

    def test_private_home_loads_interactive_configuration(self):
        argv = json.loads(self.launch().stdout)
        self.assertTrue(any('cp /home/designer/.bashrc "$HOME/.bashrc"' in a for a in argv))

    def test_make_delegates_without_docker_probe(self):
        result = subprocess.run(['make', '-n', 'start-raw', 'NO_PULL=1'], cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('./start_shell.sh', result.stdout)
        self.assertNotIn('docker', result.stderr)

    def test_ports_modes_and_literal_environment(self):
        for mode in ('vnc', 'jupyter'):
            result = self.launch(mode)
            self.assertEqual(result.returncode, 0, result.stderr)
            argv = json.loads(result.stdout)
            self.assertIn('-d', argv)
            self.assertTrue(any(a.startswith('127.0.0.1:') for a in argv))
        self.assertEqual(self.launch('vnc', VNC_PORT='65536').returncode, 2)
        self.assertEqual(self.launch('x').returncode, 2)
        self.assertEqual(self.launch(DESIGNS='/a', SHARED_DIR='/b').returncode, 2)
        result = self.launch(DESIGNS='/a path', DOCKER_USER='', DOCKER_REGISTRY='')
        self.assertIn(f'ac3e-ic-toolbox:{VERSION}', json.loads(result.stdout))
        self.assertIn('type=bind,source=/a path,target=/home/designer/shared', json.loads(result.stdout))

    def test_literal_env_precedence_and_dry_run_no_writes(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            path = Path(tmp)
            config = path / 'config'
            designs = path / 'new project'
            marker = path / 'executed'
            config.write_text(f'DOCKER_USER=other\nDESIGNS="{designs}"\nDOCKER_IMAGE=$(touch {marker})\n')
            result = self.launch(ENV_FILE=str(config), DOCKER_USER='', DOCKER_IMAGE='local')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(f'local:{VERSION}', json.loads(result.stdout))
            self.assertFalse(designs.exists())
            self.assertFalse(marker.exists())

    def test_diagnostic_redacts_tokens(self):
        result = self.launch('shell', 'tool', '--token=private-value')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('private-value', result.stdout)

    def existing_container(self, mode='x', running=False, compatible=True):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            path = Path(tmp)
            name = 'launcher-regression'
            state = [{'Config': {'Image': f'isaiash/ac3e-ic-toolbox:{VERSION}' if compatible else 'other:image'},
                      'Mounts': [{'Source': tmp, 'Destination': '/home/designer/shared'}],
                      'State': {'Running': running}}]
            (path / 'state.json').write_text(json.dumps(state))
            docker = path / 'docker'
            docker.write_text('#!/bin/bash\n'
                              'python3 -c \'import json,os,sys; open(os.environ["CALLS"], "a").write(json.dumps(sys.argv[1:])+"\\n")\' "$@"\n'
                              'if [[ $1 == container && $2 == ls ]]; then printf "%s\\n" "$CONTAINER_NAME"; fi\n'
                              'if [[ $1 == container && $2 == inspect ]]; then /bin/cat "$STATE"; fi\n')
            docker.chmod(0o755)
            result = self.launch(mode, DRY_RUN='0', PATH=tmp + ':' + os.environ['PATH'],
                                 DESIGNS=tmp, DISPLAY=':0', CONTAINER_NAME=name,
                                 DOCKER_USER='isaiash', DOCKER_IMAGE='ac3e-ic-toolbox', DOCKER_TAG=VERSION,
                                 CALLS=str(path / 'calls'), STATE=str(path / 'state.json'))
            calls = [json.loads(line) for line in (path / 'calls').read_text().splitlines()]
            return result, calls

    def test_start_resumes_compatible_stopped_container(self):
        for mode in ('x', 'shell', 'vnc', 'jupyter'):
            with self.subTest(mode=mode):
                result, calls = self.existing_container(mode)
                self.assertEqual(result.returncode, 0, result.stderr)
                expected = ['container', 'start']
                if mode in ('x', 'shell'):
                    expected += ['-ai']
                self.assertEqual(calls[-1], expected + ['launcher-regression'])
                self.assertFalse(any(call[0] in ('run', 'image') for call in calls))

    def test_start_refuses_incompatible_stopped_container(self):
        result, calls = self.existing_container(compatible=False)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('Container exists', result.stderr)
        self.assertEqual(calls[-1], ['container', 'inspect', 'launcher-regression'])

    def test_start_running_container_reports_exec_without_recreating(self):
        result, calls = self.existing_container(running=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('docker exec -it launcher-regression /bin/bash', result.stderr)
        self.assertEqual(calls[-1], ['container', 'inspect', 'launcher-regression'])

    def test_docker_failure_status_is_propagated(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            docker = Path(tmp) / 'docker'
            docker.write_text('#!/bin/bash\nif [[ $1 == container && $2 == ls ]]; then exit 0; fi\nif [[ $1 == image && $2 == inspect ]]; then exit 0; fi\nexit 7\n')
            docker.chmod(0o755)
            result = self.launch(DRY_RUN='0', PATH=tmp + ':' + os.environ['PATH'], DESIGNS=tmp)
            self.assertEqual(result.returncode, 7, result.stderr)

if __name__ == '__main__':
    unittest.main()
