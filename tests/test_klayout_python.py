"""KLayout's embedded 3.10 must not consume the user Python 3.11 environment."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / 'images/final_structure/install'
PCELLS = '/opt/klayout-pcells/lib/python3.10/site-packages'


class KLayoutPython(unittest.TestCase):
    def test_wrapper_scopes_python_path_and_preserves_arguments(self):
        wrapper = INSTALL / 'klayout'
        self.assertTrue(wrapper.is_file(), 'embedded Python 3.10 wrapper missing')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / 'klayout-deb'
            binary.write_text('#!/bin/bash\n'
                              'printf "%s\\n" "$KLAYOUT_PYTHONPATH" '
                              '"${PYTHONPATH-unset}" "$PYTHONNOUSERSITE" "$@"\n')
            binary.chmod(0o755)
            # Only replace the external binary boundary unavailable on the host.
            script = root / 'klayout'
            script.write_text(wrapper.read_text().replace('/usr/bin/klayout', str(binary)))
            env = dict(os.environ, KLAYOUT_PYTHONPATH='/custom/macros',
                       PYTHONPATH='/unrelated/python311')
            env.pop('BASH_ENV', None)
            result = subprocess.run(['bash', str(script), '-b', '-r', 'path with spaces.py'],
                                    env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(),
                             [PCELLS + ':/custom/macros', '/unrelated/python311',
                              '1', '-b', '-r', 'path with spaces.py'])
            self.assertEqual(env['KLAYOUT_PYTHONPATH'], '/custom/macros')

    def test_real_image_gate_checks_embedded_imports_and_generated_geometry(self):
        text = (ROOT / 'tests/data/gf180_klayout_smoke.py').read_text()
        self.assertIn('sys.version_info[:2] == (3, 10)', text)
        self.assertIn('import numpy', text)
        self.assertIn('import gdsfactory', text)
        self.assertIn("Path('/opt/klayout-pcells/lib/python3.10/site-packages')", text)
        self.assertIn('not cell.bbox().empty()', text)
        shell = (ROOT / 'tests/pdk/klayout-gf180-tech.sh').read_text()
        self.assertIn('klayout -b -r', shell)
        self.assertIn('rm -f "$GF_GDS_OUTPUT"', shell)
        self.assertIn("grep -q 'GF180 nfet PCell GDS:'", shell)

    def test_only_pcell_dependencies_are_installed_in_system_python_venv(self):
        text = (INSTALL / 'install_klayout.sh').read_text()
        self.assertIn('uv venv --python /usr/bin/python3.10', text)
        self.assertIn('/opt/klayout-pcells', text)
        self.assertIn('"numpy<2" "gdsfactory<8"', text)
        self.assertIn('uv pip check --python "$pcell_venv/bin/python"', text)
        self.assertIn('/usr/local/bin/klayout', text)
        self.assertNotIn('--system', text)
        self.assertNotIn('python_packages.sh', text)


if __name__ == '__main__':
    unittest.main()
