"""Opt-in real-image UID gate: UID_RUNTIME_IMAGE=... python3 -m unittest discover -s tests -p test_uid_runtime.py -v.

No builds, host mounts, or image filesystem permission/ownership changes.
"""
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.environ.get('UID_RUNTIME_IMAGE'), 'set UID_RUNTIME_IMAGE for real-image UID gate')
class UIDRuntime(unittest.TestCase):
    def test_private_writable_home_and_nix_executables(self):
        env = os.environ.copy()
        env.update(ENV_FILE='/dev/null', DRY_RUN='1', DOCKER_REGISTRY='',
                   DOCKER_USER='', DOCKER_IMAGE=os.environ['UID_RUNTIME_IMAGE'].rsplit(':', 1)[0],
                   DOCKER_TAG=os.environ['UID_RUNTIME_IMAGE'].rsplit(':', 1)[1])
        for uid, gid in (('12345', '23456'), ('1000', '1000'), ('0', '0')):
            with self.subTest(uid=uid, gid=gid):
                env.update(CONTAINER_USER=uid, CONTAINER_GROUP=gid)
                command = ['bash', str(ROOT / 'start_shell.sh'), '--print-json',
                           'bash', '--noprofile', '--norc', '-c',
                           'set -eu; test "$HOME" = /tmp/unic-cass-home; '
                           'test "$(stat -c %u:%g "$HOME")" = "$(id -u):$(id -g)"; '
                           'test "$(stat -c %a "$HOME")" = 700; '
                           'touch "$HOME/write-probe"; '
                           'test -r "$HOME/.nix-profile/etc/profile.d/nix.sh"; '
                           'test -x "$HOME/.nix-profile/bin/librelane"; '
                           'test -z "${LD_LIBRARY_PATH:-}"; librelane --version']
                dry = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
                argv = json.loads(dry.stdout)
                # Do not expose designs or require a TTY; use only private tmpfs.
                index = argv.index('--mount')
                del argv[index:index + 2]
                argv.remove('-it')
                index = argv.index('--name')
                del argv[index:index + 2]
                argv.insert(2, '--rm')
                result = subprocess.run(argv, capture_output=True, text=True, timeout=120)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('LibreLane', result.stdout)


if __name__ == '__main__':
    unittest.main()
