"""Python 3.11 is a user runtime, not a replacement for Ubuntu Python."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'images/final_structure/configure'


class PythonRuntime(unittest.TestCase):
    def test_image_has_a_real_interpreter_and_dependency_gate(self):
        script = ROOT / 'tests/inventory/python.sh'
        self.assertTrue(script.is_file(), 'real-image Python integration gate missing')
        text = script.read_text()
        self.assertIn('sys.version_info[:2] == (3, 11)', text)
        self.assertIn('/usr/bin/python3', text)
        self.assertIn('uv pip check', text)

    def test_user_python_precedes_nix_without_changing_system_python(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            venv = root / 'eda-venv'
            (venv / 'bin').mkdir(parents=True)
            python = venv / 'bin/python'
            python.write_text('#!/bin/sh\nprintf "user-python-3.11\\n"\n')
            python.chmod(0o755)
            nix = root / '.nix-profile/etc/profile.d'
            nix.mkdir(parents=True)
            (root / 'nix-bin').mkdir()
            (nix / 'nix.sh').write_text(
                f'case ":$PATH:" in *":{root}/nix-bin:"*) ;; '
                f'*) export PATH="{root}/nix-bin:$PATH" ;; esac\n')
            pdk = root / 'pdks/ihp-sg13g2'
            (pdk / 'libs.tech').mkdir(parents=True)
            (pdk / 'libs.ref/sg13g2_stdcell').mkdir(parents=True)
            env = dict(os.environ, HOME=str(root), EDA_VENV=str(venv),
                       TOOLS=str(root / 'tools'), PDK_ROOT=str(root / 'pdks'),
                       DESIGNS=str(root / 'designs'), PATH='/usr/bin:/bin')
            env.pop('BASH_ENV', None)
            result = subprocess.run(
                ['bash', '--noprofile', '--norc', '-c',
                 f'set -eu; source "{CONFIG}/ac3e-ic-toolbox-env.sh" >/dev/null; '
                 'before=$PATH; '
                 f'source "{CONFIG}/ac3e-ic-toolbox-env.sh" >/dev/null; '
                 'test "$before" = "$PATH"; command -v python; python'],
                env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), [str(python), 'user-python-3.11'])

    def test_runtime_dependencies_install_into_python311_venv(self):
        installer = (ROOT / 'images/base/python_packages.sh').read_text()
        self.assertIn('uv venv --python /opt/python/bin/python3.11', installer)
        self.assertIn('--python "$EDA_VENV/bin/python"', installer)
        self.assertNotIn('uv pip install --system', installer)
        self.assertIn('uv pip check', installer)

    def test_python_source_is_verified_and_system_python_is_not_relinked(self):
        installer = ROOT / 'images/python/install.sh'
        self.assertTrue(installer.is_file(), 'side-by-side Python installer missing')
        text = installer.read_text()
        self.assertIn('sha256sum --check', text)
        self.assertIn('make altinstall', text)
        self.assertNotIn('/usr/bin/python', text)
        dockerfile = (ROOT / 'Dockerfile').read_text()
        self.assertIn('AS python_builder', dockerfile)
        self.assertIn('COPY --from=python_builder /opt/python /opt/python', dockerfile)
        self.assertIn('EDA_VENV=/opt/eda-venv', dockerfile)


if __name__ == '__main__':
    unittest.main()
