"""CVC fixtures must survive Windows-style Git checkout settings."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = (
    'tests/data/analog/cvc.cvcrc',
    'tests/data/analog/cvc-inverter.cdl',
    'tests/data/analog/cvc-models',
    'tests/data/analog/cvc-power',
)


class CvcLineEndings(unittest.TestCase):
    def test_checkout_keeps_fixtures_lf_with_autocrlf_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            shutil.copyfile(ROOT / '.gitattributes', repo / '.gitattributes')
            for name in FIXTURES:
                target = repo / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
            for autocrlf in ('false', 'true'):
                subprocess.run(
                    ['git', '-C', str(repo), 'config', 'core.autocrlf', autocrlf],
                    check=True,
                )
                for name in FIXTURES:
                    (repo / name).unlink()
                subprocess.run(
                    ['git', '-C', str(repo), 'checkout-index', '-a', '-f'], check=True,
                )
                for name in FIXTURES:
                    with self.subTest(autocrlf=autocrlf, fixture=name):
                        self.assertNotIn(b'\r', (repo / name).read_bytes())

    def test_crlf_configuration_is_rejected_before_running_cvc(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'analog').mkdir()
            (root / 'data/analog').mkdir(parents=True)
            shutil.copyfile(ROOT / 'tests/analog/cvc-electrical.sh', root / 'analog/cvc-electrical.sh')
            for name in FIXTURES:
                data = (ROOT / name).read_bytes()
                if name.endswith('.cvcrc'):
                    data = data.replace(b'\n', b'\r\n')
                (root / 'data/analog' / Path(name).name).write_bytes(data)
            # Isolate the host test from the container-only environment and binary.
            (root / 'common.sh').write_text(
                'load_design_env() { :; }\n'
                'require_command() { :; }\n'
                'fail() { printf "%s\\n" "$1" >&2; exit 1; }\n'
                'cvc_rv() { touch "$TEST_ROOT/cvc-invoked"; return 0; }\n'
            )
            env = os.environ.copy()
            env.pop('BASH_ENV', None)
            result = subprocess.run(
                ['bash', str(root / 'analog/cvc-electrical.sh')],
                env=env, capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('CVC configuration contains CRLF line endings; LF is required.', result.stderr)
            self.assertFalse((root / 'cvc-invoked').exists())


if __name__ == '__main__':
    unittest.main()
