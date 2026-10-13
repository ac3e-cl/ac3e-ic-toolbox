"""Exercise the bootstrap without downloading an image or starting Docker."""
import os
import pty
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Quickstart(unittest.TestCase):
    def test_missing_python_fails_before_creating_checkout(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            base = Path(tmp)
            for command in ('git', 'make', 'jq', 'docker'):
                (base / command).symlink_to('/bin/true')
            destination = base / 'checkout'
            result = subprocess.run(['/bin/bash', str(ROOT / 'quickstart.sh'), str(destination)],
                                    env=dict(os.environ, PATH=str(base), DISPLAY=':0'),
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('Required command not found: python3', result.stderr)
            self.assertFalse(destination.exists())

    def test_missing_display_fails_before_creating_checkout(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            destination = Path(tmp) / 'checkout'
            env = dict(os.environ, DISPLAY='')
            result = subprocess.run(['bash', str(ROOT / 'quickstart.sh'), str(destination)],
                                    env=env, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('DISPLAY', result.stderr)
            self.assertFalse(destination.exists())

    def test_main_checkout_then_make_start_with_literal_destination(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            base = Path(tmp)
            commands = base / 'bin'
            commands.mkdir()
            log = base / 'calls'
            for name, body in {
                'docker': 'printf "docker %s\\n" "$*" >> "$CALL_LOG"',
                'git': 'printf "git %s\\n" "$*" >> "$CALL_LOG"; mkdir -- "${@: -1}"',
                'make': 'printf "make %s in %s\\n" "$*" "$PWD" >> "$CALL_LOG"',
            }.items():
                script = commands / name
                script.write_text('#!/usr/bin/env bash\nset -eu\n' + body + '\n')
                script.chmod(0o755)
            destination = base / 'my tools'
            env = dict(os.environ, PATH=f'{commands}:{os.environ["PATH"]}',
                       DISPLAY=':0', CALL_LOG=str(log))
            master, slave = pty.openpty()
            try:
                result = subprocess.run(['bash', str(ROOT / 'quickstart.sh'), str(destination)],
                                        stdin=slave, env=env, text=True, capture_output=True)
            finally:
                os.close(master)
                os.close(slave)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(log.read_text().splitlines(), [
                'docker info',
                f'git clone --depth 1 --single-branch --branch main -- https://github.com/unic-cass/uniccass-icdesign-tools.git {destination}',
                f'make start in {destination}',
            ])
            result = subprocess.run(['bash', str(ROOT / 'quickstart.sh'), str(destination)],
                                    env=env, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('already exists', result.stderr)
            self.assertEqual(len(log.read_text().splitlines()), 3)


if __name__ == '__main__':
    unittest.main()
