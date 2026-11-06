"""Host-side tests for the strict GF180 report oracle (no EDA dependency)."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "gf_rules", Path(__file__).parent / "helpers/gf180-rules.py")
assert SPEC is not None and SPEC.loader is not None
gf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gf)


class ReportOracleTests(unittest.TestCase):
    def test_real_report_counts_and_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.lyrdb"
            report.write_text("""<report-database><categories>
<category><name>DF.11</name></category><category><name>CO.5a</name></category>
</categories><items><item><category>'DF.11'</category><cell>TOP</cell>
<values><value>edge: (0,0;0,0.2)</value></values></item></items></report-database>""")
            counts, geometry = gf.parse_report(report)
            self.assertEqual(counts, {"DF.11": 1, "CO.5a": 0})
            self.assertEqual(len(geometry[('TOP', 'DF.11')]), 1)
            gf.check_counts(counts, {"DF.11": 1, "CO.5a": 0})
            with self.assertRaises(AssertionError):
                gf.check_counts(counts, {"DF.11": 0})
            with self.assertRaises(AssertionError):
                gf.check_counts(counts, {"MISSING": 0})

    def test_missing_categories_are_not_a_clean_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "empty.lyrdb"
            report.write_text('<report-database><items/></report-database>')
            with self.assertRaises(ValueError):
                gf.parse_report(report)


if __name__ == '__main__':
    unittest.main()
