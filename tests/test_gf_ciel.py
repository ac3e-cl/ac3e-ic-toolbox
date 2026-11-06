"""Host contracts for the global Ciel installation (no EDA tools required)."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PIN = '792ef67037d74c8c51811eab3ce23cf793491296'


class CielIntegrity(unittest.TestCase):
    def test_missing_root_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            result = subprocess.run(['python3', str(ROOT / 'images/pdks/gf180_integrity.py'),
                                     'links', str(Path(tmp) / 'absent')], capture_output=True)
            self.assertNotEqual(result.returncode, 0)

    def test_ciel_requires_matching_backing_and_all_libraries(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('integrity', ROOT / 'images/pdks/gf180_integrity.py')
        assert spec is not None and spec.loader is not None
        integrity = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(integrity)
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = Path(tmp)
            backing = root / f'ciel/gf180mcu/versions/{PIN}/gf180mcuD'
            backing.mkdir(parents=True)
            (root / 'gf180mcuD').symlink_to(backing)
            (root / 'ciel/gf180mcu/current').write_text(PIN)
            with self.assertRaisesRegex(RuntimeError, 'missing PDK resource'):
                integrity.check_ciel(root, PIN)
            for resource in integrity.REQUIRED_RESOURCES:
                path = backing / 'libs.tech' / resource
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('fixture, not an EDA result')
            for library in integrity.REQUIRED_LIBRARIES:
                (backing / 'libs.ref' / library).mkdir(parents=True)
            integrity.check_ciel(root, PIN)
            (root / 'ciel/gf180mcu/current').write_text('0' * 40)
            with self.assertRaisesRegex(RuntimeError, 'current'):
                integrity.check_ciel(root, PIN)


class CielInstaller(unittest.TestCase):
    def test_installer_uses_pinned_ciel_without_legacy_build(self):
        text = (ROOT / 'images/pdks/install_gf180mcu.sh').read_text()
        self.assertNotIn('prepare_open_pdks', text)
        self.assertNotIn('volare ', text)
        self.assertNotIn('git ', text)
        self.assertIn('ciel enable', text)
        self.assertIn('--pdk-root "$PDK_ROOT"', text)
        self.assertIn('--pdk gf180mcuD', text)
        self.assertIn('--include-libraries all', text)
        self.assertIn('CIEL_VERSION', text)
        self.assertIn('GF180_PDK_COMMIT', text)

    def test_missing_or_wrong_ciel_version_fails_before_download(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = Path(tmp)
            exe = root / 'ciel'
            exe.write_text('#!/bin/bash\nif [[ "$1" == --version ]]; then echo "Ciel v2.0.0"; else touch "$PDK_ROOT/downloaded"; fi\n')
            exe.chmod(0o755)
            env = dict(os.environ, PATH=f'{root}:{os.environ["PATH"]}',
                       PDK_ROOT=tmp, CIEL_VERSION='3.1.0', GF180_PDK_COMMIT=PIN)
            result = subprocess.run(['bash', str(ROOT / 'images/pdks/install_gf180mcu.sh')],
                                    env=env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Ciel version mismatch', result.stderr)
            self.assertFalse((root / 'downloaded').exists())
