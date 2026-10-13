"""Release publication must follow both host and image tests."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CIContract(unittest.TestCase):
    def test_headless_release_has_gui_test_dependencies(self):
        text = (ROOT / 'images/base/base_install.sh').read_text()
        runtime_dependencies = text.split('GUI_DEPS=(')[0]
        for package in ('xvfb', 'x11-utils'):
            self.assertIn(package, runtime_dependencies)

    def test_shell_checks_validate_every_script(self):
        text = (ROOT / '.github/workflows/docker-release.yml').read_text()
        self.assertIn('for script in', text)
        self.assertIn('quickstart.sh', text)
        self.assertIn('images/base/*.sh', text)
        self.assertIn('bash -n "$script"', text)

    def test_checkout_includes_contract_baseline_history(self):
        text = (ROOT / '.github/workflows/docker-release.yml').read_text()
        self.assertIn('fetch-depth: 0', text)

    def test_publication_remains_gated(self):
        text = (ROOT / '.github/workflows/docker-release.yml').read_text()
        checks = text.index('python3 -m unittest discover')
        build = text.index('- name: Build release image')
        integration = text.index('- name: Run integration tests')
        login = text.index('- name: Log in to Docker Hub')
        push = text.index('- name: Push release image')
        self.assertLess(checks, build)
        self.assertLess(build, integration)
        self.assertLess(integration, login)
        self.assertLess(login, push)
        self.assertIn('CHECK_ONLY=1 ./build/build-image.sh', text)
        self.assertIn('environment: release-env', text)

    def test_failure_logs_survive_until_upload(self):
        text = (ROOT / '.github/workflows/docker-release.yml').read_text()
        self.assertNotIn('trap cleanup EXIT', text)
        self.assertLess(text.index('actions/upload-artifact@'),
                        text.index('- name: Clean integration output'))
        self.assertIn('if: ${{ failure() }}', text)


if __name__ == '__main__':
    unittest.main()
