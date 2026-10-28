import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'images/final_structure/configure'

class PdkContract(unittest.TestCase):
    def test_retired_pdk_build_resources_are_removed(self):
        for path in ('images/pdks/install_sky130.sh',
                     'images/final_structure/configure/patch_pdk_sky130.sh',
                     'images/librelane/sky/bootstrap.sh',
                     'images/librelane/sky/flake.nix'):
            with self.subTest(path=path):
                self.assertFalse((ROOT / path).exists())

    def test_open_pdks_preparation_rejects_retired_family_before_fetching(self):
        r = self.bash(f'git() {{ return 71; }}; rm() {{ return 71; }}; source "{ROOT}/images/pdks/prepare_open_pdks.sh"; prepare_open_pdks sky130')
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn('Unsupported PDK family: sky130', r.stderr)

    def test_technology_patcher_rejects_removed_pdk(self):
        r = subprocess.run(['python3', str(CONFIG / 'fix-tech-file.py'),
                            '--pdk', 'sky130A', 'unused.lyt'], text=True, capture_output=True)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn('invalid choice', r.stderr)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.base = pathlib.Path(self.tmp.name)
        self.env = dict(os.environ, HOME=str(self.base), PDK_ROOT=str(self.base / 'pdks'), TOOLS=str(self.base / 'tools'), DESIGNS=str(self.base / 'designs'))
        for pdk, lib in [('ihp-sg13g2', 'sg13g2_stdcell'), ('sky130A', 'sky130_fd_sc_hd'), ('gf180mcuD', 'gf180mcu_fd_sc_mcu7t5v0')]:
            for sub in ['libs.tech/ngspice', 'libs.tech/klayout', 'libs.tech/xschem', 'libs.tech/magic', 'libs.ref/' + lib]:
                (self.base / 'pdks' / pdk / sub).mkdir(parents=True, exist_ok=True)
    def bash(self, script):
        return subprocess.run(['bash', '--noprofile', '--norc', '-c', script], env=self.env, text=True, capture_output=True)
    def test_transaction_and_switch(self):
        r = self.bash(f'''set -eu; source "{CONFIG}/pdk.sh"; sak-pdk gf180mcuD; before=$(export -p); for bad in gf180mcuC sky130A sky130B GF missing; do set_pdk "$bad" && exit 1; test $? = 2; test "$(export -p)" = "$before"; done; set_pdk gf180mcuD ../bad && exit 1; test $? = 2; test "$(export -p)" = "$before"; set_pdk ihp-sg13g2; test -z "${{GF_PDK_OPTION+x}}"''')
        self.assertEqual(r.returncode, 0, r.stderr)
    def test_library_and_listing(self):
        (self.base / 'pdks/gf180mcuD/libs.ref/custom').mkdir()
        r = self.bash(f'''set -eu; source "{CONFIG}/pdk.sh"; sak-pdk gf180mcuD custom; test "$STD_CELL_LIBRARY" = custom; set_pdk gf180mcuD custom; sak-pdk''')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.endswith('ihp-sg13g2\ngf180mcuD\n'))
    def test_gf_contract(self):
        r = self.bash(f'set -eu; source "{CONFIG}/pdk.sh"; sak-pdk gf180mcuD; test "$GF_PDK_OPTION" = D; test "$PDKPATH" = "$PDK_ROOT/gf180mcuD"; test "$STD_CELL_LIBRARY" = gf180mcu_fd_sc_mcu7t5v0')
        self.assertEqual(r.returncode, 0, r.stderr)
