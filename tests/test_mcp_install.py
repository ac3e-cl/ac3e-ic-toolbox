"""Contracts for the bundled, isolated stdio MCP launcher."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MCPInstallTests(unittest.TestCase):
    def test_launcher_uses_private_python_and_preserves_arguments(self):
        launcher = ROOT / 'images/mcp/ac3e-ic-toolbox-mcp'
        self.assertTrue(launcher.exists(), 'Bundled MCP launcher is missing')
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory)
            (prefix / 'venv/bin').mkdir(parents=True)
            python = prefix / 'venv/bin/python'
            python.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n')
            python.chmod(0o755)
            result = subprocess.run(['bash', str(launcher), '--workspace', '/a design'],
                                    env={**os.environ, 'AC3E_IC_TOOLBOX_MCP_HOME': directory},
                                    capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(),
                             ['-I', str(prefix / 'server.py'), '--workspace', '/a design'])

    def test_final_image_installs_mcp(self):
        dockerfile = (ROOT / 'Dockerfile').read_text()
        self.assertIn('source=images/mcp,target=/images/mcp', dockerfile)
        self.assertIn('bash /images/mcp/install.sh', dockerfile)

    def test_installer_copies_all_server_modules(self):
        installer = (ROOT / 'images/mcp/install.sh').read_text()
        for module in ('server', 'filesystem', 'eda'):
            self.assertIn(f'"$source_dir/{module}.py" "$prefix/{module}.py"', installer)


if __name__ == '__main__':
    unittest.main()
