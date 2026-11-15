"""Exercise Windows startup at the process boundary without a Windows host."""
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VcXsrv(unittest.TestCase):
    def test_authority_is_private_reused_and_passed_to_windows(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            for name, body in {
                'wslpath': 'import sys; print(sys.argv[-1])',
                'powershell.exe': 'import os,sys,json; open(os.environ["CALLS"], "a").write(json.dumps(sys.argv[1:])+"\\n")',
            }.items():
                path = home / name
                path.write_text('#!/usr/bin/env python3\n' + body + '\n')
                path.chmod(0o755)
            env = dict(os.environ, HOME=tmp, PATH=tmp + ':' + os.environ['PATH'],
                       DISPLAY='host.docker.internal:0', CALLS=str(home / 'calls'))
            env.pop('XAUTHORITY', None)
            command = ['python3', str(ROOT / 'runtime/vcxsrv.py')]
            first = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            authority = Path(first.stdout.strip())
            data = authority.read_bytes()
            self.assertEqual(authority.stat().st_mode & 0o777, 0o600)
            family = struct.unpack('>H', data[:2])[0]
            self.assertEqual(family, 65535)  # FamilyWild: Docker/WSL address independent.
            fields = []
            offset = 2
            for _ in range(4):
                size = struct.unpack('>H', data[offset:offset + 2])[0]
                offset += 2
                fields.append(data[offset:offset + size])
                offset += size
            self.assertEqual(fields[:3], [b'', b'0', b'MIT-MAGIC-COOKIE-1'])
            self.assertEqual(len(fields[3]), 16)
            second = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(authority.read_bytes(), data)
            calls = [json.loads(line) for line in (home / 'calls').read_text().splitlines()]
            self.assertEqual(len(calls), 2)
            self.assertEqual(calls[0][-2:], ['-AuthorityFile', str(authority)])
            self.assertIn(str(ROOT / 'runtime/start-vcxsrv.ps1'), calls[0])

    def test_windows_launcher_selects_vcxsrv_and_server_uses_multiwindow(self):
        self.assertIn('if defined AC3E_XSERVER', (ROOT / 'start.bat').read_text())
        script = (ROOT / 'runtime/start-vcxsrv.ps1').read_text()
        self.assertIn("'-multiwindow'", script)
        self.assertIn("'-auth'", script)
        self.assertNotIn("'-ac'", script)


if __name__ == '__main__':
    unittest.main()
