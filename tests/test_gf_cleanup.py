import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
HELPER = ROOT / 'images/pdks/gf180_integrity.py'

class Cleanup(unittest.TestCase):
    def test_private_backing_remains_readable(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = pathlib.Path(tmp)
            backing = root / 'volare/gf180mcu/versions/pin'
            (backing / 'gf180mcuA').mkdir(parents=True)
            (backing / 'gf180mcuD').mkdir()
            (backing / 'gf180mcuA/resource').write_text('rules')
            (backing / 'gf180mcuD/shared').symlink_to('../gf180mcuA', target_is_directory=True)
            for variant in 'AD':
                (root / ('gf180mcu' + variant)).symlink_to(backing / ('gf180mcu' + variant))
            subprocess.run(['python3', str(HELPER), 'hide', str(root)], check=True)
            self.assertFalse((root / 'gf180mcuA').exists())
            self.assertEqual((root / 'gf180mcuD/shared/resource').read_text(), 'rules')

    def test_broken_link_under_linked_directory_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = pathlib.Path(tmp)
            (root / 'external').mkdir()
            (root / 'D').mkdir()
            (root / 'D/linked').symlink_to(root / 'external')
            (root / 'external/broken').symlink_to('absent')
            result = subprocess.run(['python3', str(HELPER), 'links', str(root / 'D')], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'broken', result.stderr)
