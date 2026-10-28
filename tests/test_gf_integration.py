import pathlib
import json
import re
import unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
class Integration(unittest.TestCase):
    def test_inventory_covers_host_manifest_without_mounting_it(self):
        text = (ROOT / 'tests/inventory/tools.sh').read_text()
        arguments = json.loads((ROOT / 'manifest.json').read_text())['build']['arguments']
        expected = {key for key in arguments if key.endswith('_NAME')}
        covered = set(re.findall(r"'([A-Z0-9_]+_NAME)'\s*:", text))
        self.assertEqual(expected, covered)
        self.assertNotIn('/home/designer/manifest.json', text)
    def test_existing_pdk_tests_are_discovered(self):
        text = (ROOT / 'tests/run_all.sh').read_text()
        self.assertIn('find analog digital gui inventory pdk', text)
        names = ['layout-extraction.sh', 'klayout-ihp-drc.sh',
                 'ngspice-ihp-mosfet.sh',
                 'librelane-template-ihp.sh', 'librelane-template-gf.sh',
                 'pdk-environment.sh', 'ngspice-gf180-mosfet.sh',
                 'klayout-gf180-tech.sh', 'librelane-gf180-smoke.sh']
        for name in names:
            self.assertTrue((ROOT / 'tests/pdk' / name).is_file(), name)
    def test_full_digital_flow_has_output_gates(self):
        text = (ROOT / 'tests/pdk/librelane-gf180-smoke.sh').read_text()
        self.assertIn('--pdk gf180mcuD', text)
        self.assertIn('metrics.json', text)
        self.assertIn('*.gds', text)
        self.assertNotIn('--smoke-test', text)
