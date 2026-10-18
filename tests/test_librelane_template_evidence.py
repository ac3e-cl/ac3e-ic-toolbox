"""Require real flow and simulation artifacts, including negative controls."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TemplateEvidence(unittest.TestCase):
    def test_rejects_failed_simulation_even_when_flow_has_gds(self):
        path = ROOT / 'tests/helpers/verify_librelane_template.py'
        self.assertTrue(path.is_file(), 'artifact verification is missing')
        spec = importlib.util.spec_from_file_location('evidence', path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / 'final'
            final.mkdir()
            (final / 'metrics.json').write_text(json.dumps({'design__instance__count': 5}))
            (final / 'chip.gds').write_bytes(b'test fixture only')
            xml = root / 'rtl.xml'
            xml.write_text('<testsuite><testcase name="counter"><failure/></testcase></testsuite>')
            with self.assertRaises(AssertionError):
                module.verify(final, [xml])
            xml.write_text('<testsuite><testcase name="counter"/></testsuite>')
            evidence = module.verify(final, [xml])
            self.assertEqual(evidence['simulation_tests'], 1)
            (final / 'chip.gds').unlink()
            with self.assertRaises(AssertionError):
                module.verify(final, [xml])


if __name__ == '__main__':
    unittest.main()
