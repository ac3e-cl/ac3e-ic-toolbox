"""The pinned CVC header must include array without rewriting upstream CRLF."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'images/cvc_rv/gcc12_compat.py'


class CVCGCC12Tests(unittest.TestCase):
    def test_adds_array_and_preserves_mixed_line_endings(self):
        for newline in (b'\n', b'\r\n'):
            with self.subTest(newline=newline), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'CCircuit.hh'
                original = b'#ifndef CCIRCUIT_HH_' + newline + b'#include "Cvc.hh"' + newline + b'// unchanged\n'
                path.write_bytes(original)
                subprocess.run(['python3', str(HELPER), str(path)], check=True)
                expected = original.replace(b'#include "Cvc.hh"', b'#include <array>' + newline + b'#include "Cvc.hh"')
                self.assertEqual(path.read_bytes(), expected)
                subprocess.run(['python3', str(HELPER), str(path)], check=True)
                self.assertEqual(path.read_bytes(), expected)

    def test_unexpected_header_is_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'CCircuit.hh'
            original = b'// unexpected upstream header\n'
            path.write_bytes(original)
            result = subprocess.run(['python3', str(HELPER), str(path)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(path.read_bytes(), original)

    def test_installer_applies_fix_before_compilation(self):
        text = (ROOT / 'images/cvc_rv/install.sh').read_text()
        self.assertIn('gcc12_compat.py', text)
        self.assertLess(text.index('gcc12_compat.py'), text.index('make -j'))


if __name__ == '__main__':
    unittest.main()
