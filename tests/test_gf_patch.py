import pathlib
import unittest
import tempfile
import os
import subprocess
import hashlib

class PatchBehavior(unittest.TestCase):
    def test_patch_handles_cross_device_directory_move(self):
        self.test_patch_twice_preserves_resources(cross_device=True)

    def test_patch_twice_preserves_resources(self, cross_device=False):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = pathlib.Path(tmp)
            tech = root / 'gf180mcuD/libs.tech'
            k = tech / 'klayout'
            for folder in ['tech', 'pymacros/efuse', 'macros', 'drc', 'lvs']:
                (k / folder).mkdir(parents=True)
            (tech / 'xschem').mkdir()
            (tech / 'xschem/xschemrc').write_text('append XSCHEM_LIBRARY_PATH :$env(PWD)\nset 180MCU_MODELS ${PDK_ROOT}/models/ngspice\n')
            tags = ['description', 'group', 'base-path', 'original-base-path', 'layer-properties_file', 'add-other-layers', 'reader-options', 'writer-options', 'd25']
            (k / 'tech/gf180mcu.lyt').write_text('<technology>' + ''.join('<'+t+'></'+t+'>' for t in tags) + '</technology>')
            (k / 'tech/gf180mcu.lym').write_text('macro')
            (k / 'pymacros/efuse/efuse.gds').write_bytes(b'fixture resource, not an EDA result')
            (k / 'pymacros/__init__.py').write_text('# fixture')
            (k / 'macros/gf180mcu_options.lym').write_text(';"C" ], 2)')
            (k / 'macros/drc_options.yml').write_text('variant: C')
            for folder in ['drc', 'lvs']:
                (k / folder / 'rules').write_text('preserve')
            env = dict(os.environ, PDK_ROOT=str(root))
            if cross_device:
                (root / 'sitecustomize.py').write_text(
                    'import os, errno\n'
                    'original = os.rename\n'
                    'def rename(src, dst, *args, **kwargs):\n'
                    '    if os.path.isdir(src) and not os.path.islink(src):\n'
                    '        raise OSError(errno.EXDEV, "Invalid cross-device link")\n'
                    '    return original(src, dst, *args, **kwargs)\n'
                    'os.rename = rename\n')
                env['PYTHONPATH'] = str(root)
            script = ROOT / 'images/final_structure/configure/patch_pdk_gf180mcu.sh'
            subprocess.run(['bash', str(script)], env=env, check=True, capture_output=True)
            def snapshot():
                return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}
            before = snapshot()
            subprocess.run(['bash', str(script)], env=env, check=True, capture_output=True)
            self.assertEqual(before, snapshot())
            self.assertEqual((k / 'drc/rules').read_text(), 'preserve')
            self.assertEqual((k / 'lvs/rules').read_text(), 'preserve')
            self.assertIn('$env(PDK_ROOT)/gf180mcuD/libs.tech/ngspice', (tech / 'xschem/xschemrc').read_text())
ROOT = pathlib.Path(__file__).resolve().parents[1]
class PatchContract(unittest.TestCase):
    def test_patch_is_offline(self):
        text = (ROOT / 'images/final_structure/configure/patch_pdk_gf180mcu.sh').read_text()
        self.assertNotIn('git clone', text)
        self.assertNotIn('|| true', text)
    def test_installer_preserves_rules_and_backing(self):
        text = (ROOT / 'images/pdks/install_gf180mcu.sh').read_text()
        self.assertNotIn('rm -rf $PDK_ROOT/volare/gf180mcu/versions/$OPEN_PDKS_REPO_COMMIT/gf180mcuA', text)
        self.assertNotIn('/tech/drc', text)
