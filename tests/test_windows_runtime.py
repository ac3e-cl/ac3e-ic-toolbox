"""Native Git Bash/MSYS regressions; no EDA image or user container required."""
import json
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get('TEST_BASH') or shutil.which('bash')
# Packaged app aliases may not be executable by a child outside that package.
if os.name == 'nt' and Path('C:/Program Files/Git/bin/bash.exe').is_file():
    BASH = 'C:/Program Files/Git/bin/bash.exe'


@unittest.skipUnless(os.name == 'nt' and BASH, 'requires native Windows and Git Bash/MSYS')
class WindowsRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='windows-runtime-', dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.env = dict(os.environ)
        for key in ('DESIGNS', 'SHARED_DIR', 'CONTAINER_USER', 'CONTAINER_GROUP', 'USER_ID',
                    'USER_GROUP', 'ROOT', 'DISPLAY', 'XAUTHORITY', 'AC3E_XSERVER', 'BASH_ENV'):
            self.env.pop(key, None)
        self.env.pop('MSYS_NO_PATHCONV', None)
        self.env.pop('MSYS2_ARG_CONV_EXCL', None)
        self.env.update(ENV_FILE=str(self.directory / 'absent.env'), DRY_RUN='1',
                        DOCKER_IMAGE='windows-regression', DOCKER_TAG='test',
                        DOCKER_USER='', DOCKER_REGISTRY='', NO_PULL='1')

    def launch(self, mode='x', *args, code=None):
        command = [BASH, '--noprofile', '--norc']
        if code:
            command += ['-c', code, 'windows-test', str(ROOT / 'runtime/start.sh'), mode, *args]
        else:
            command += [str(ROOT / 'runtime/start.sh'), mode, '--print-json', *args]
        return subprocess.run(command, env=self.env, text=True, capture_output=True)

    def fake_docker(self, state=None):
        shim = self.directory / 'docker-shim.py'
        self.log = self.directory / 'docker.jsonl'
        self.log.unlink(missing_ok=True)
        self.env.update(SHIM=shim.as_posix(), DOCKER_LOG=str(self.log),
                        DOCKER_STATE=json.dumps(state), DRY_RUN='0',
                        SHARED_DIR=self.directory.as_posix())
        shim.write_text('''import json, os, sys
args = sys.argv[1:]
with open(os.environ['DOCKER_LOG'], 'a') as stream:
    stream.write(json.dumps(args) + '\\n')
state = json.loads(os.environ['DOCKER_STATE'])
if args[:2] == ['container', 'ls'] and state:
    print('windows-regression-owned')
elif args[:2] == ['container', 'inspect']:
    print(json.dumps([state]))
''')
        (self.directory / 'docker').write_text('#!/usr/bin/env bash\nexec python3 "$SHIM" "$@"\n')
        self.env['CONTAINER_NAME'] = 'windows-regression-owned'

    def fake_launch(self, mode='vnc'):
        return self.launch(mode, code='export PATH="$(cygpath -u "${SHIM%/*}"):$PATH"; exec bash "$1" "$2"')

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_docker_boundary_preserves_container_paths_with_conversion_enabled(self):
        self.fake_docker()
        result = self.fake_launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        run = next(args for args in self.calls() if args[0] == 'run')
        self.assertEqual(run[run.index('--entrypoint')+1], '/bin/bash')
        self.assertIn('HOME=/tmp/ac3e-ic-toolbox-home', run)

        self.assertIn('type=bind,source='+self.directory.as_posix()+',target=/home/designer/shared', run)

    def state(self, source=None, **state):
        return {'Config': {'Image': 'windows-regression:test', 'Env': [],
                           'Labels': {'org.ac3e.ic-toolbox.mode': 'vnc'}},
                'State': {'Running': False, 'Status': 'exited', 'StartedAt': '2026-01-01T00:00:00Z', **state},
                'Mounts': [{'Source': source or self.directory.as_posix(),
                            'Destination': '/home/designer/shared'}]}

    def test_reuses_docker_desktop_normalized_windows_mount(self):
        source = '/run/desktop/mnt/host/' + self.directory.drive[0].lower() + self.directory.as_posix()[2:]
        for path in (source, source.replace('/', '\\'), str(self.directory),
                     self.directory.as_posix().lower()):
            with self.subTest(path=path):
                self.fake_docker(self.state(path))
                result = self.fake_launch()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(['container', 'start', 'windows-regression-owned'], self.calls())
                self.assertFalse(any(args[0] == 'run' for args in self.calls()))

    def test_failed_created_container_requires_consent_with_actionable_recovery(self):
        state = self.state(Status='created', StartedAt='0001-01-01T00:00:00Z',
                           Error='exec: C:/Program Files/Git/usr/bin/bash: no such file')
        state['Mounts'][0]['Source'] = 'C:/old/path'
        self.fake_docker(state)
        result = self.fake_launch()
        self.assertEqual(result.returncode, 2)
        self.assertIn('never started', result.stderr)
        self.assertIn('interactively', result.stderr)
        self.assertIn('docker container rm', result.stderr)
        self.assertFalse(any(args[:2] == ['container', 'rm'] for args in self.calls()))
        self.assertFalse(any(args[0] == 'run' for args in self.calls()))

    def test_started_container_is_never_treated_as_failed_creation(self):
        state = self.state(Status='exited', Error='old startup failure')
        state['Mounts'][0]['Source'] = 'C:/old/path'
        self.fake_docker(state)
        result = self.fake_launch()
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('never started', result.stderr)
        self.assertFalse(any(args[:2] == ['container', 'rm'] for args in self.calls()))

    def test_native_windows_defaults_and_absolute_bind_paths(self):
        shared = self.directory / 'designs with spaces'
        shared.mkdir()
        authority = self.directory / 'cookie with spaces'
        authority.touch()
        self.env['XAUTHORITY'] = str(authority)
        for path in (shared.as_posix(), str(shared), '/'+shared.drive[0].lower()+shared.as_posix()[2:]):
            with self.subTest(path=path):
                self.env['SHARED_DIR'] = path
                result = self.launch()
                self.assertEqual(result.returncode, 0, result.stderr)
                argv = json.loads(result.stdout)
                self.assertEqual(argv[argv.index('--user')+1], '1000:1000')
                self.assertIn('DISPLAY=host.docker.internal:0', argv)
                self.assertIn('LIBGL_ALWAYS_INDIRECT=1', argv)
                self.assertIn('type=bind,source='+shared.as_posix()+',target=/home/designer/shared', argv)
                self.assertIn('type=bind,source='+(ROOT/'tests').as_posix()+',target=/home/designer/tests', argv)
                self.assertIn('type=bind,source='+authority.as_posix()+',target=/tmp/.Xauthority,readonly', argv)
                self.assertEqual(argv[argv.index('--entrypoint')+1], '/bin/bash')

    def test_windows_auto_ignores_inherited_external_display(self):
        for display in ('localhost:1.0', '127.0.0.1:10.0', 'remote.example:2'):
            with self.subTest(display=display):
                self.env['DISPLAY'] = display
                result = self.launch()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('DISPLAY=host.docker.internal:0', json.loads(result.stdout))
        self.env.update(AC3E_XSERVER='native', DISPLAY='remote.example:2')
        result = self.launch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('DISPLAY=remote.example:2', json.loads(result.stdout))

    def test_linux_darwin_and_wsl_display_selection_is_preserved(self):
        self.fake_docker()
        self.env.update(DRY_RUN='1', SHARED_DIR='/tmp/simulated-designs')
        scenarios = [('Linux', ':14', '', '', False),
                     ('Darwin', 'host.docker.internal:14', '', '', False),
                     ('Linux', ':0', 'interop', 'wayland-0', False),
                     ('Linux', ':0', 'interop', '', True)]
        for system, display, interop, wayland, vcxsrv in scenarios:
            with self.subTest(system=system, interop=interop, wayland=wayland):
                (self.directory/'uname').write_text('#!/usr/bin/env bash\nprintf "%s\\n" '+system+'\n')
                self.env.update(DISPLAY=display, WSL_INTEROP=interop, WAYLAND_DISPLAY=wayland)
                result = self.launch('x', '--print-json', code='export PATH="$(cygpath -u "${SHIM%/*}"):$PATH"; exec bash "$1" "$2" "${@:3}"')
                self.assertEqual(result.returncode, 0, result.stderr)
                argv = json.loads(result.stdout)
                self.assertIn('DISPLAY='+('host.docker.internal:0' if vcxsrv else display), argv)
                self.assertEqual('LIBGL_ALWAYS_INDIRECT=1' in argv, vcxsrv)
                self.assertEqual('type=bind,source=/tmp/.X11-unix,target=/tmp/.X11-unix,readonly' in argv,
                                 display.startswith(':') and not vcxsrv)

    def test_reuses_normalized_windows_authority_mount(self):
        authority = self.directory/'cookie with spaces'
        authority.touch()
        state = self.state()
        state['Config']['Labels']['org.ac3e.ic-toolbox.mode'] = 'x'
        state['Config']['Env'] = ['DISPLAY=external.example:0']
        source = '/host_mnt/'+authority.drive[0].lower()+authority.as_posix()[2:]
        state['Mounts'].append({'Source': source, 'Destination': '/tmp/.Xauthority'})
        self.fake_docker(state)
        self.env.update(AC3E_XSERVER='native', DISPLAY='external.example:0', XAUTHORITY=str(authority))
        result = self.fake_launch('x')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(['container', 'start', '-ai', 'windows-regression-owned'], self.calls())

    def test_vcxsrv_native_python_does_not_require_wsl(self):
        spec = importlib.util.spec_from_file_location('windows_vcxsrv', ROOT/'runtime/vcxsrv.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        output = io.StringIO()
        with patch.dict(os.environ, {'USERPROFILE': str(self.directory), 'HOME': str(self.directory),
                                     'DISPLAY': 'host.docker.internal:0', 'XAUTHORITY': ''}), \
                patch.object(module.subprocess, 'run') as run, \
                contextlib.redirect_stdout(output):
            module.main()
        authority = Path(output.getvalue().strip())
        self.assertTrue(authority.is_file())
        command = run.call_args.args[0]
        self.assertEqual(command[0], 'powershell.exe')
        self.assertEqual(Path(command[command.index('-File')+1]), ROOT/'runtime/start-vcxsrv.ps1')
        self.assertEqual(Path(command[command.index('-AuthorityFile')+1]), authority)

    def test_x_launcher_normalizes_authority_before_and_after_native_helper(self):
        self.fake_docker()
        authority = self.directory / 'cookie with spaces'
        authority.touch()
        self.env['XAUTHORITY'] = '/' + authority.drive[0].lower() + authority.as_posix()[2:]
        self.env['REAL_PYTHON'] = sys.executable
        (self.directory / 'python3').write_text('''#!/usr/bin/env bash
if [[ $1 == */vcxsrv.py ]]; then
    [[ $XAUTHORITY == [A-Za-z]:/* ]] || { echo 'authority must be native' >&2; exit 9; }
    printf '%s\\r\\n' "$XAUTHORITY"
else exec "$REAL_PYTHON" "$@"; fi
''')
        result = self.fake_launch('x')
        self.assertEqual(result.returncode, 0, result.stderr)
        run = next(args for args in self.calls() if args[0] == 'run')
        self.assertIn('type=bind,source='+authority.as_posix()+',target=/tmp/.Xauthority,readonly', run)

    @unittest.skipUnless(os.environ.get('RUN_WINDOWS_DOCKER_TESTS') == '1', 'opt-in real Docker validation')
    def test_real_docker_bootstrap_binds_reuse_and_failed_creation_safety(self):
        name = 'ac3e-windows-regression-' + uuid.uuid4().hex[:12]
        image = os.environ['WINDOWS_TEST_IMAGE']
        self.env.update(CONTAINER_NAME=name, DOCKER_IMAGE=image.rsplit(':', 1)[0],
                        DOCKER_TAG=image.rsplit(':', 1)[1], SHARED_DIR=self.directory.as_posix())
        def docker(*args, check=True):
            return subprocess.run(['docker', *args], text=True, capture_output=True, check=check)
        try:
            result = self.launch('shell', '/bin/bash', '-lc',
                                 'test -d /home/designer/tests; echo verified > /home/designer/shared/probe; cat /home/designer/shared/probe')
            self.assertEqual(result.returncode, 0, result.stderr)
            argv = json.loads(result.stdout)
            argv.remove('-it')  # CI has no interactive console; all other arguments are real.
            run = docker(*argv[1:])
            self.assertIn('verified', run.stdout)
            self.assertEqual((self.directory/'probe').read_text().strip(), 'verified')
            before = json.loads(docker('container', 'inspect', name).stdout)[0]
            self.assertEqual(before['Config']['Entrypoint'], ['/bin/bash'])
            self.assertEqual(before['State']['ExitCode'], 0)
            self.assertEqual(before['Config']['User'], '1000:1000')
            self.env['DRY_RUN'] = '0'
            reused = self.launch('shell')
            self.assertEqual(reused.returncode, 0, reused.stderr)
            after = json.loads(docker('container', 'inspect', name).stdout)[0]
            self.assertEqual(before['Id'], after['Id'])
            self.assertIn('verified', reused.stdout)
            print('REAL DOCKER:', name, before['Id'], json.dumps(before['Mounts']))
            docker('container', 'rm', name)
            failed = docker('run', '--name', name, '--entrypoint', '/missing-windows-regression', image, check=False)
            self.assertNotEqual(failed.returncode, 0)
            stale = json.loads(docker('container', 'inspect', name).stdout)[0]
            self.assertEqual(stale['State']['Status'], 'created')
            refused = self.launch('vnc')
            self.assertEqual(refused.returncode, 2, refused.stderr)
            self.assertIn('never started', refused.stderr)
            self.assertEqual(json.loads(docker('container', 'inspect', name).stdout)[0]['Id'], stale['Id'])
        finally:
            docker('container', 'rm', '-f', name, check=False)
            remaining = docker('container', 'ls', '-a', '--filter', 'name=^/'+name+'$', '--format', '{{.Names}}')
            self.assertEqual(remaining.stdout.strip(), '')


if __name__ == '__main__':
    unittest.main()
