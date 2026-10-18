"""Stable launcher identity and consent-based image replacement."""
import json
import os
import pty
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ContainerLifecycle(unittest.TestCase):
    def scenario(self, *, image='old:1', running=False, answer=None, local=True,
                 remote='sha256:old', pull_fails=False, no_pull=False, mount=None, stored_mode='x',
                 local_id='sha256:old-image', mode='x', repo_digests=None):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            base = Path(tmp)
            manifest = json.loads((ROOT / 'manifest.json').read_text())
            reference = f"isaiash/ac3e-ic-toolbox:{manifest['release']['version']}"
            if image == 'current':
                image = reference
            state = [{'Config': {'Image': image, 'Labels': {'org.ac3e.ic-toolbox.mode': stored_mode}}, 'Image': 'sha256:old-image',
                      'Mounts': [{'Source': mount or tmp, 'Destination': '/home/designer/shared'}],
                      'State': {'Running': running}}]
            (base / 'state.json').write_text(json.dumps(state))
            docker = base / 'docker'
            docker.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
a=sys.argv[1:]
with open(os.environ['CALLS'], 'a') as f: f.write(json.dumps(a)+'\\n')
if a[:2]==['container','ls']: print('ac3e-ic-toolbox')
elif a[:2]==['container','inspect']: print(Path(os.environ['STATE']).read_text())
elif a[:2]==['image','inspect']:
    if os.environ['LOCAL']=='0': sys.exit(1)
    print(json.dumps([{'Id':os.environ['LOCAL_ID'],'RepoDigests':json.loads(os.environ['DIGESTS'])}]))
elif a[:3]==['buildx','imagetools','inspect']:
    if os.environ['REMOTE']=='offline': sys.exit(1)
    print(json.dumps({'digest':os.environ['REMOTE']}))
elif a[:2]==['image','pull'] and os.environ['PULL_FAIL']=='1': sys.exit(7)
elif a[0] in ('run','exec') or a[:2] in (['container','start'],['container','rm'],['container','stop'],['image','pull']): pass
else: sys.exit(8)
''')
            docker.chmod(0o755)
            env = dict(os.environ, PATH=tmp + ':' + os.environ['PATH'], ENV_FILE='/dev/null',
                       DESIGNS=tmp, DISPLAY=':0', LOCAL=str(int(local)), REMOTE=remote,
                       PULL_FAIL=str(int(pull_fails)), LOCAL_ID=local_id,
                       DIGESTS=json.dumps(['isaiash/ac3e-ic-toolbox@sha256:old'] if repo_digests is None else repo_digests),
                       CALLS=str(base / 'calls'), STATE=str(base / 'state.json'))
            for key in ('CONTAINER_NAME', 'DRY_RUN', 'NO_PULL', 'SHARED_DIR', 'DOCKER_IMAGE',
                        'DOCKER_USER', 'DOCKER_TAG', 'DOCKER_REGISTRY'):
                env.pop(key, None)
            if no_pull:
                env['NO_PULL'] = '1'
            master, slave = pty.openpty()
            try:
                process = subprocess.Popen(['bash', str(ROOT / 'runtime/start.sh'), mode],
                                           env=env, stdin=slave if answer is not None else subprocess.DEVNULL,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                os.close(slave)
                if answer is not None:
                    os.write(master, (answer + '\n').encode())
                out, err = process.communicate(timeout=10)
            finally:
                os.close(master)
            calls = [json.loads(line) for line in (base / 'calls').read_text().splitlines()]
            return process.returncode, out + err, calls

    def test_version_change_confirmed_pulls_before_removing_then_recreates(self):
        code, output, calls = self.scenario(answer='y', local=False, running=True)
        self.assertEqual(code, 0, output)
        pull = next(i for i, a in enumerate(calls) if a[:2] == ['image', 'pull'])
        remove = next(i for i, a in enumerate(calls) if a[:2] == ['container', 'rm'])
        run = next(i for i, a in enumerate(calls) if a[0] == 'run')
        self.assertLess(pull, remove)
        self.assertLess(remove, run)
        self.assertIn('mounted', output)

    def test_published_update_prompts_before_pull_and_replacement(self):
        code, output, calls = self.scenario(image='current', answer='y', remote='sha256:new')
        self.assertEqual(code, 0, output)
        self.assertIn('Update', output)
        self.assertTrue(any(a[:2] == ['image', 'pull'] for a in calls))
        self.assertTrue(any(a[:2] == ['container', 'rm'] for a in calls))

    def test_refuses_reusing_another_service_mode(self):
        code, output, calls = self.scenario(image='current', stored_mode='vnc')
        self.assertEqual(code, 2, output)
        self.assertFalse(any(a[0] in ('run', 'exec') or a[:2] == ['container', 'start'] for a in calls))

    def test_x_mode_rejects_shell_container_without_display_mounts(self):
        code, output, calls = self.scenario(image='current', stored_mode='shell', running=True)
        self.assertEqual(code, 2, output)
        self.assertFalse(any(a[0] in ('run', 'exec') for a in calls))

    def test_raw_shell_can_reuse_x_capable_container(self):
        code, output, calls = self.scenario(image='current', stored_mode='x', mode='shell', running=True)
        self.assertEqual(code, 0, output)
        self.assertEqual(calls[-1], ['exec', '-it', 'ac3e-ic-toolbox', '/bin/bash'])

    def test_local_build_without_digests_never_probes_registry(self):
        code, output, calls = self.scenario(image='current', answer='y', repo_digests=[], remote='sha256:new')
        self.assertEqual(code, 0, output)
        self.assertFalse(any(a[:3] == ['buildx', 'imagetools', 'inspect'] or a[:2] == ['image', 'pull'] for a in calls))

    def test_test_mode_uses_disposable_name(self):
        env = dict(os.environ, DRY_RUN='1', ENV_FILE='/dev/null')
        env.pop('CONTAINER_NAME', None)
        result = subprocess.run(['bash', str(ROOT / 'runtime/start.sh'), 'test', '--print-json'],
                                env=env, text=True, capture_output=True, check=True)
        argv = json.loads(result.stdout)
        self.assertRegex(argv[argv.index('--name') + 1], r'^ac3e-ic-toolbox-test-\d+$')

    def test_decline_or_enter_never_changes_existing_container(self):
        for image, remote in [('old:1', 'sha256:old'), ('current', 'sha256:new')]:
            for answer in ('n', ''):
                with self.subTest(image=image, answer=answer):
                    code, output, calls = self.scenario(image=image, remote=remote, answer=answer)
                    self.assertEqual(code, 0, output)
                    self.assertIn('kept unchanged', output)
                    self.assertFalse(any(a[0] in ('run', 'exec') or a[:2] in
                                         (['container', 'rm'], ['container', 'stop'], ['image', 'pull']) for a in calls))

    def test_version_change_uses_cached_image_without_pull(self):
        code, output, calls = self.scenario(answer='yes')
        self.assertEqual(code, 0, output)
        self.assertTrue(any(a[0] == 'run' for a in calls))
        self.assertFalse(any(a[:2] == ['image', 'pull'] for a in calls))

    def test_pull_failure_preserves_running_container(self):
        code, output, calls = self.scenario(answer='y', local=False, running=True, pull_fails=True)
        self.assertEqual(code, 7, output)
        self.assertFalse(any(a[:2] in (['container', 'stop'], ['container', 'rm']) for a in calls))

    def test_noninteractive_version_change_is_not_destructive(self):
        code, output, calls = self.scenario()
        self.assertEqual(code, 2, output)
        self.assertIn('confirm replacement', output)
        self.assertFalse(any(a[:2] in (['container', 'rm'], ['image', 'pull']) for a in calls))

    def test_no_pull_blocks_download_for_missing_version(self):
        code, output, calls = self.scenario(answer='y', local=False, no_pull=True)
        self.assertEqual(code, 2, output)
        self.assertFalse(any(a[:2] in (['image', 'pull'], ['container', 'rm']) for a in calls))

    def test_same_version_reuses_stopped_container_without_download(self):
        code, output, calls = self.scenario(image='current', answer='n')
        self.assertEqual(code, 0, output)
        self.assertEqual(calls[-1], ['container', 'start', '-ai', 'ac3e-ic-toolbox'])
        self.assertFalse(any(a[:2] == ['image', 'pull'] for a in calls))

    def test_running_same_version_opens_another_shell(self):
        code, output, calls = self.scenario(image='current', running=True)
        self.assertEqual(code, 0, output)
        self.assertEqual(calls[-1], ['exec', '-it', 'ac3e-ic-toolbox', '/bin/bash'])

    def test_registry_unavailable_keeps_current_container(self):
        code, output, calls = self.scenario(image='current', answer='y', remote='offline')
        self.assertEqual(code, 0, output)
        self.assertIn('Update check unavailable', output)
        self.assertEqual(calls[-1], ['container', 'start', '-ai', 'ac3e-ic-toolbox'])

    def test_local_rebuild_prompts_but_does_not_pull(self):
        code, output, calls = self.scenario(image='current', answer='y', local_id='sha256:rebuilt')
        self.assertEqual(code, 0, output)
        self.assertIn('locally installed', output)
        self.assertTrue(any(a[:2] == ['container', 'rm'] for a in calls))
        self.assertFalse(any(a[:2] == ['image', 'pull'] for a in calls))

    def test_changed_mount_is_never_silently_reused_or_removed(self):
        code, output, calls = self.scenario(image='current', answer='y', mount='/other')
        self.assertEqual(code, 2, output)
        self.assertFalse(any(a[0] in ('run', 'exec') or a[:2] == ['container', 'rm'] for a in calls))

    def test_default_name_is_manifest_name_not_mode_or_uid(self):
        for mode in ('x', 'shell', 'attach', 'vnc', 'jupyter'):
            with self.subTest(mode=mode):
                env = dict(os.environ, DRY_RUN='1', ENV_FILE='/dev/null', DISPLAY=':0')
                env.pop('CONTAINER_NAME', None)
                result = subprocess.run(['bash', str(ROOT / 'runtime/start.sh'), mode, '--print-json'],
                                        env=env, text=True, capture_output=True, check=True)
                argv = json.loads(result.stdout)
                self.assertEqual(argv[argv.index('--name') + 1], 'ac3e-ic-toolbox')


if __name__ == '__main__':
    unittest.main()
