"""Protect the existing tool selection and the shared runtime installation."""
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '69cca4d'
# Intentional addition to the historical tool selection, not a prefix exemption.
GNUCAP_ARGUMENTS = {
    'GNUCAP_REPO_URL': 'https://codeberg.org/gnucap/gnucap.git',
    'GNUCAP_REPO_COMMIT': 'bcaff61b3c562179476bb6c5de783676994c61e1',
    'GNUCAP_NAME': 'gnucap',
}


class RepositoryContract(unittest.TestCase):
    def baseline(self, path):
        return subprocess.check_output(
            ['git', 'show', f'{BASELINE}:{path}'], cwd=ROOT, text=True)

    def test_tool_pins_are_unchanged(self):
        before = json.loads(self.baseline('manifest.json'))
        after = json.loads((ROOT / 'manifest.json').read_text())
        self.assertTrue(GNUCAP_ARGUMENTS.keys().isdisjoint(before['build']['arguments']))
        expected_arguments = {**before['build']['arguments'], **GNUCAP_ARGUMENTS}
        # Debian migration changes the base/packaging, not upstream tool pins.
        expected_arguments.update(BASE_IMAGE='debian:bookworm-slim', KLAYOUT_DOWNLOAD='')
        expected_arguments['OPENVAF_RUST_VERSION'] = '1.74.1'
        self.assertEqual(expected_arguments, after['build']['arguments'])
        self.assertEqual(after['build']['target'], 'ac3e-ic-toolbox')
        self.assertEqual(before['image']['registry'], after['image']['registry'])
        self.assertEqual(after['image']['namespace'], 'isaiash')
        self.assertEqual(after['image']['name'], 'ac3e-ic-toolbox')

    def test_no_new_tool_stages_or_final_copies(self):
        before = self.baseline('Dockerfile')
        after = (ROOT / 'Dockerfile').read_text()
        stages = lambda text: re.findall(r'^FROM .* AS (\S+)', text, re.M)
        copies = lambda text: [line.split() for line in text.splitlines()
                               if line.startswith('COPY --from=')]
        expected_stages = stages(before)[:-2]
        expected_stages.insert(expected_stages.index('xyce'), 'gnucap')
        expected_stages[expected_stages.index('magic'):expected_stages.index('magic')] = [
            'heavyweight_builder', 'openroad_dependencies']
        expected_stages[expected_stages.index('open_pdks'):expected_stages.index('open_pdks')] = [
            'pdk_builder', 'sky130_pdk', 'gf180_pdk']
        # KLayout is rebuilt on Debian instead of installing an Ubuntu binary.
        expected_stages.insert(expected_stages.index('heavyweight_builder'), 'klayout')
        # The final two stages are renamed, not new tools or a separate Nix variant.
        self.assertEqual(stages(after)[:-2], expected_stages)
        self.assertEqual(stages(after)[-2:], ['ac3e-ic-toolbox-base', 'ac3e-ic-toolbox'])
        expected_copies = copies(before)
        expected_copies.insert(0, ['COPY', '--from=klayout', '/opt/klayout', '/opt/klayout'])
        ngspice_copy = ['COPY', '--from=ngspice', '${TOOLS}/ngspice', '${TOOLS}/ngspice']
        expected_copies.insert(expected_copies.index(ngspice_copy) + 1,
                               ['COPY', '--from=gnucap', '${TOOLS}/gnucap', '${TOOLS}/gnucap'])
        # Explicit structural additions only: retain the final tool inventory and
        # copy the entire PDK roots so Volare-relative links remain resolvable.
        expected_copies[:0] = [
            ['COPY', '--from=sky130_pdk', '${PDK_ROOT}', '${PDK_ROOT}'],
            ['COPY', '--from=gf180_pdk', '${PDK_ROOT}', '${PDK_ROOT}'],
        ]
        common_copy = expected_copies.index(
            ['COPY', '--from=builder', '${TOOLS}/common', '${TOOLS}/common'])
        expected_copies[common_copy][1] = '--from=openroad_dependencies'
        self.assertEqual(copies(after), expected_copies)

    def test_runtime_config_is_installed_once(self):
        dockerfile = (ROOT / 'Dockerfile').read_text()
        self.assertIn('COPY images/final_structure/configure/profile.sh /opt/ac3e-ic-toolbox/config/', dockerfile)
        self.assertIn('COPY images/final_structure/configure/pdk.sh', dockerfile)
        self.assertIn('/opt/ac3e-ic-toolbox/config/', dockerfile)
        self.assertIn('/etc/profile.d/ac3e-ic-toolbox.sh', dockerfile)
        self.assertIn('ln -s /opt/pdks /foss/pdks', dockerfile)
        self.assertIn('ln -s /home/designer/shared /foss/designs', dockerfile)
        self.assertNotIn('ac3e-ic-toolbox-temp', dockerfile)

    def test_shell_startup_sources_installed_profile(self):
        dockerfile = (ROOT / 'Dockerfile').read_text()
        match = re.search(
            r'^COPY images/final_structure/configure/profile\.sh (\S+)/$',
            dockerfile, re.M)
        self.assertIsNotNone(match)
        assert match is not None
        destination = match.group(1)
        for name in ('.bashrc', 'etc_bash.bashrc_nix'):
            with self.subTest(startup=name):
                text = (ROOT / 'images/final_structure/configure' / name).read_text()
                self.assertIn(f'[[ -f {destination}/profile.sh ]]', text)
                self.assertIn(f'source {destination}/profile.sh', text)

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
