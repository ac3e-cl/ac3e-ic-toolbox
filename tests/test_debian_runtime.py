"""Contracts for the Debian 12 / Python 3.11 build and isolated EDA packages."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DebianRuntimeTests(unittest.TestCase):
    def test_base_matches_manifest(self):
        manifest = json.loads((ROOT / 'manifest.json').read_text())
        self.assertEqual(manifest['build']['arguments']['BASE_IMAGE'], 'debian:bookworm-slim')
        self.assertIn('ARG BASE_IMAGE=debian:bookworm-slim', (ROOT / 'Dockerfile').read_text())

    def test_eda_packages_do_not_mutate_system_python(self):
        for name in ('base/python_packages.sh', 'builder/exhaustive-install.sh'):
            text = (ROOT / 'images' / name).read_text()
            self.assertNotIn('pip install --system', text)
            self.assertIn('"$EDA_PYTHON/bin/python"', text)
            self.assertIn('pip check', text)
        dockerfile = (ROOT / 'Dockerfile').read_text()
        self.assertIn('EDA_PYTHON=/opt/eda-python', dockerfile)
        self.assertIn('ENV PATH="/opt/eda-python/bin:$PATH"', dockerfile)

    def test_klayout_is_built_on_debian_at_existing_revision(self):
        dockerfile = (ROOT / 'Dockerfile').read_text()
        self.assertIn('FROM builder AS klayout', dockerfile)
        self.assertIn('COPY --from=klayout', dockerfile)
        installer = (ROOT / 'images/klayout/install.sh').read_text()
        self.assertIn('"$KLAYOUT_REPO_COMMIT"', installer)
        self.assertIn('${MAX_BUILD_JOBS:-2}', installer)
        self.assertNotIn('dpkg -i', (ROOT / 'images/final_structure/install/install_klayout.sh').read_text())

    def test_embedded_klayout_can_find_eda_venv_packages(self):
        installer = (ROOT / 'images/final_structure/install/install_klayout.sh').read_text()
        self.assertIn('"$EDA_PYTHON/bin/python"', installer)
        self.assertIn('/opt/klayout/bin/.python-paths.txt', installer)


if __name__ == '__main__':
    unittest.main()
