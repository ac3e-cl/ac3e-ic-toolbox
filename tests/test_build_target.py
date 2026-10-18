"""The standard image target must include Nix and use local stages."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildTarget(unittest.TestCase):
    def test_standard_target_is_the_final_nix_stage(self):
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        text = (ROOT / 'Dockerfile').read_text()
        stages = re.findall(r'^FROM\s+(\S+)(?:\s+AS\s+(\S+))?\s*$', text, re.M)
        target = manifest['build']['target']
        self.assertEqual(target, 'ac3e-ic-toolbox')
        self.assertEqual(stages[-1], ('ac3e-ic-toolbox-base', target))
        self.assertIn(('base', 'ac3e-ic-toolbox-base'), stages)
        final = text.split(f'FROM ac3e-ic-toolbox-base AS {target}\n')[1]
        self.assertIn('ARG NIX_INSTALLER_URL', final)
        self.assertIn('nix profile install .', final)
        self.assertIn('librelane --version', final)


if __name__ == '__main__':
    unittest.main()
