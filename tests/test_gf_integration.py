import pathlib
import re
import unittest
ROOT = pathlib.Path(__file__).resolve().parents[1]
class Integration(unittest.TestCase):
    def test_eight_real_tests_registered(self):
        text = (ROOT / 'shared_xserver/tests/run-all.sh').read_text()
        names = re.findall(r'([\w-]+\.sh)', text.split('tests=(', 1)[1].split(')', 1)[0])
        self.assertEqual(len(names), 8)
        for name in names:
            self.assertTrue((ROOT / 'shared_xserver/tests' / name).is_file(), name)
    def test_full_digital_flow_has_output_gates(self):
        text = (ROOT / 'shared_xserver/tests/librelane-gf180-smoke.sh').read_text()
        self.assertIn('--pdk gf180mcuD', text)
        self.assertIn('metrics.json', text)
        self.assertIn('*.gds', text)
        self.assertNotIn('--smoke-test', text)
