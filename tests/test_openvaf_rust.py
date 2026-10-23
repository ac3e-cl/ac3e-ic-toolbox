"""OpenVAF must not depend on Debian's old rustc or update upstream Cargo pins."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OpenVAFRustTests(unittest.TestCase):
    def test_build_uses_manifest_pinned_private_toolchain(self):
        args = json.loads((ROOT / 'manifest.json').read_text())['build']['arguments']
        self.assertEqual(args['OPENVAF_RUST_VERSION'], '1.74.1')
        dockerfile = (ROOT / 'Dockerfile').read_text()
        self.assertEqual(dockerfile.count('ARG OPENVAF_RUST_VERSION'), 2)
        installer = (ROOT / 'images/openvaf/install.sh').read_text()
        self.assertIn('--default-toolchain "$OPENVAF_RUST_VERSION"', installer)
        self.assertIn('--no-modify-path', installer)
        self.assertIn('CARGO_HOME=', installer)
        self.assertIn('RUSTUP_HOME=', installer)
        self.assertIn('--locked', installer)
        self.assertNotIn('cargo update', installer)
        self.assertIn('rm -rf "$rust_build_home"', installer)


if __name__ == '__main__':
    unittest.main()
