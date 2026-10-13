"""Protect the existing tool selection and the shared runtime installation."""
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'fbee49843948c4c7ca5ab126ef02d9be1335c580'


class RepositoryContract(unittest.TestCase):
    def baseline(self, path):
        return subprocess.check_output(
            ['git', 'show', f'{BASELINE}:{path}'], cwd=ROOT, text=True)

    def test_tool_pins_are_unchanged(self):
        before = json.loads(self.baseline('manifest.json'))
        after = json.loads((ROOT / 'manifest.json').read_text())
        self.assertEqual(before['build'], after['build'])
        self.assertEqual(before['image'], after['image'])

    def test_no_new_tool_stages_or_final_copies(self):
        before = self.baseline('Dockerfile')
        after = (ROOT / 'Dockerfile').read_text()
        stages = lambda text: set(re.findall(r'^FROM .* AS (\S+)', text, re.M))
        copies = lambda text: set(re.findall(r'^COPY --from=(\S+)', text, re.M))
        self.assertLessEqual(stages(after), stages(before))
        self.assertEqual(copies(after), copies(before))

    def test_runtime_config_is_installed_once(self):
        dockerfile = (ROOT / 'Dockerfile').read_text()
        self.assertIn('COPY images/final_structure/configure/profile.sh /opt/unic-cass/config/', dockerfile)
        self.assertIn('COPY images/final_structure/configure/pdk.sh', dockerfile)
        self.assertIn('/opt/unic-cass/config/', dockerfile)
        self.assertIn('/etc/profile.d/unic-cass-tools.sh', dockerfile)
        self.assertIn('ln -s /opt/pdks /foss/pdks', dockerfile)
        self.assertIn('ln -s /home/designer/shared /foss/designs', dockerfile)
        self.assertNotIn('unic-cass-tools-temp', dockerfile)

    def test_build_mount_sources_exist(self):
        text = (ROOT / 'Dockerfile').read_text()
        active = '\n'.join(line for line in text.splitlines()
                           if not line.lstrip().startswith('#'))
        for path in re.findall(r'--mount=type=bind,source=([^, ]+)', active):
            with self.subTest(source=path):
                self.assertTrue((ROOT / path).exists())

    def test_build_context_excludes_private_and_generated_data(self):
        lines = (ROOT / '.dockerignore').read_text().splitlines()
        for pattern in ['.git', '.hermes', '.env', 'tests/run',
                        'IDEA.md', 'shared']:
            self.assertIn(pattern, lines)


if __name__ == '__main__':
    unittest.main()
