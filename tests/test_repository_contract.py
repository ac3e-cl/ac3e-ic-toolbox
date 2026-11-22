"""Protect the existing tool selection and the shared runtime installation."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = json.loads((ROOT / 'tests/data/build-baseline.json').read_text())
# An explicit runtime addition; all existing tool/PDK revisions remain unchanged.
PYTHON_ARGUMENTS = {
    'PYTHON_VERSION': '3.11.18',
    'PYTHON_SOURCE_SHA256': '9120e0a653868f6e3698d36cdd99e5a58903ec9469e448f21d98f7b16d8fa290',
}
# Retained legacy scheduling argument for compatibility; Ciel downloads do not
# perform the former memory-heavy Volare/Magic conversion.
PDK_JOB_ARGUMENTS = {
    'PDK_BUILD_JOBS': '1',
}

# Only explicitly authorized changes may differ from the snapshot.
# Do not refresh the baseline to hide unrelated pin changes.
GF_ARGUMENTS = {
    'CIEL_VERSION': '3.1.0',
    'CIEL_REPO_COMMIT': 'e180507a4190462d65cdded4448eb4f7bd2f30fa',
    'GF180_PDK_COMMIT': '792ef67037d74c8c51811eab3ce23cf793491296',
}
GF_TEMPLATE_REVISIONS = {
    'commit': 'd99f6e1ba14e549e80d5d83e113fbd82ed37ed5c',
    'librelaneCommit': '99148a9c1e648cdfdb9d7b772481af32e0dfbe8b',
    'pdkCommit': GF_ARGUMENTS['GF180_PDK_COMMIT'],
}
IHP_ARGUMENTS = {
    'IHP_PDK_REPO_COMMIT': 'e73adb4045731ddec21634146d536380057f6a26',
    'IHP_PDK_REPO_BRANCH': 'main',
}
MODELGEN_ARGUMENTS = {
    'GNUCAP_MODELGEN_REPO_URL': 'https://codeberg.org/gnucap/gnucap-modelgen-verilog.git',
    'GNUCAP_MODELGEN_REPO_COMMIT': '0c7f045dd88a8a143631a0d2c87a0db2849762c8',
}


class RepositoryContract(unittest.TestCase):
    def test_only_authorized_build_pins_change(self):
        # A checked-in snapshot works in shallow clones and source archives too.
        before = BASELINE['manifest']
        after = json.loads((ROOT / 'manifest.json').read_text())
        self.assertTrue(PYTHON_ARGUMENTS.keys().isdisjoint(before['build']['arguments']))
        self.assertTrue(PDK_JOB_ARGUMENTS.keys().isdisjoint(before['build']['arguments']))
        self.assertTrue(GF_ARGUMENTS.keys().isdisjoint(before['build']['arguments']))
        expected_arguments = {**before['build']['arguments'], **PYTHON_ARGUMENTS,
                              **PDK_JOB_ARGUMENTS, **GF_ARGUMENTS, **IHP_ARGUMENTS,
                              **MODELGEN_ARGUMENTS,
                              'OPENVAF_REPO_URL': 'https://github.com/pascalkuthe/OpenVAF.git'}
        self.assertEqual(expected_arguments, after['build']['arguments'])
        self.assertEqual(after['librelaneTemplates'], {
            'ihp': before['librelaneTemplates']['ihp'],
            'gf': {**before['librelaneTemplates']['gf'], **GF_TEMPLATE_REVISIONS},
        })
        self.assertEqual(after['build']['target'], 'ac3e-ic-toolbox')
        self.assertEqual(before['image']['registry'], after['image']['registry'])
        self.assertEqual(after['image']['namespace'], 'isaiash')
        self.assertEqual(after['image']['name'], 'ac3e-ic-toolbox')
        self.assertEqual(after['build']['arguments']['OPENVAF_REPO_URL'],
                         'https://github.com/pascalkuthe/OpenVAF.git')

    def test_private_ihp_template_remains_frozen(self):
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        self.assertEqual(manifest['librelaneTemplates']['ihp'],
                         BASELINE['manifest']['librelaneTemplates']['ihp'])

    def test_no_new_tool_stages_or_final_copies(self):
        after = (ROOT / 'Dockerfile').read_text()
        stages = lambda text: re.findall(r'^FROM .* AS (\S+)', text, re.M)
        copies = lambda text: [line.split() for line in text.splitlines()
                               if line.startswith('COPY --from=')]
        expected_stages = list(BASELINE['stages'])
        expected_stages.remove('sky130_pdk')
        expected_stages.insert(expected_stages.index('base'), 'python_builder')
        expected_stages.insert(expected_stages.index('gnucap') + 1, 'gnucap_ihp_moslv')
        self.assertEqual(stages(after), expected_stages)
        expected_copies = [row for row in BASELINE['copies']
                           if row[1] != '--from=sky130_pdk']
        expected_copies.insert(0, ['COPY', '--from=python_builder', '/opt/python', '/opt/python'])
        old_gnucap = ['COPY', '--from=gnucap', '${TOOLS}/gnucap', '${TOOLS}/gnucap']
        gnucap_idx = expected_copies.index(old_gnucap)
        expected_copies[gnucap_idx:gnucap_idx + 1] = [
            ['COPY', '--from=gnucap', '/gnucap-dist/usr/local/', '/usr/local/'],
            ['COPY', '--from=gnucap_ihp_moslv', '/gnucap-ihp-moslv/',
             '${PDK_ROOT}/${IHP_PDK_NAME}/libs.tech/gnucap/plugins/models/'],
        ]
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
