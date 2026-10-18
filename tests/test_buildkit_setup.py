"""Build command selection without requiring a Docker daemon."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'build/buildkit-setup.sh'


class BuildkitSetup(unittest.TestCase):
    def run_setup(self, **settings):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            docker = path / 'docker'
            docker.write_text('#!/usr/bin/env python3\nimport json,os,sys\nwith open(os.environ["CALLS"],"a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\nif sys.argv[1:3] == ["buildx","inspect"]:\n print(os.environ.get("INSPECTION", "")); sys.exit(0 if "INSPECTION" in os.environ else 1)\nif "--buildkitd-config" in sys.argv:\n p=sys.argv[sys.argv.index("--buildkitd-config")+1]\n open(os.environ["CONFIG"],"w").write(open(p).read())\n')
            docker.chmod(0o755)
            env = {k: v for k, v in os.environ.items() if not k.startswith(('BUILD_', 'BUILDX_'))}
            env.update(PATH=f'{path}:{env["PATH"]}', CALLS=str(path/'calls'), CONFIG=str(path/'config'), **settings)
            result = subprocess.run(['bash', '-c', 'set -euo pipefail; source "$1"; configure_buildkit; printf "%s\\n" "${BUILD_COMMAND[@]}"', 'test', str(HELPER)], env=env, text=True, capture_output=True)
            calls = [json.loads(line) for line in (path/'calls').read_text().splitlines()] if (path/'calls').exists() else []
            config = (path/'config').read_text() if (path/'config').exists() else ''
            return result, calls, config

    def test_default_preserves_docker_build_and_cache(self):
        result, calls, _ = self.run_setup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['docker', 'build'])
        self.assertEqual(calls, [])

    def test_registry_output_never_loads_into_docker(self):
        result, calls, _ = self.run_setup(
            BUILD_OUTPUT='registry', BUILD_BUILDER='ci-builder',
            BUILD_METADATA_FILE='/work/result.json')
        self.assertEqual(result.returncode, 0, result.stderr)
        args = result.stdout.splitlines()
        self.assertNotIn('--load', args)
        self.assertIn('type=registry,compression=gzip,compression-level=1', args)
        self.assertIn('--metadata-file', args)
        self.assertIn('/work/result.json', args)

    def test_registry_requires_explicit_builder_and_metadata(self):
        for settings in ({}, {'BUILD_BUILDER': 'ci-builder'}):
            result, calls, _ = self.run_setup(BUILD_OUTPUT='registry', **settings)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(calls, [])

    def test_unknown_output_is_rejected_before_docker(self):
        result, calls, _ = self.run_setup(BUILD_OUTPUT='typo')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(calls, [])

    def test_opt_in_creates_bounded_builder_and_loads_output(self):
        result, calls, config = self.run_setup(BUILD_MAX_PARALLELISM='2')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['docker', 'buildx', 'build', '--builder', 'ac3e-ic-toolbox-p2', '--load'])
        self.assertIn('[worker.oci]\n  max-parallelism = 2', config)
        create = next(call for call in calls if call[:2] == ['buildx', 'create'])
        self.assertIn('docker-container', create)
        self.assertNotIn('--use', create)

    def test_runtime_env_passes_build_settings_to_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'runtime').mkdir()
            (root / 'build').mkdir()
            (root / 'runtime/start.sh').write_bytes((ROOT / 'runtime/start.sh').read_bytes())
            (root / 'manifest.json').write_bytes((ROOT / 'manifest.json').read_bytes())
            wrapper = root / 'build/build-image.sh'
            wrapper.write_text('#!/usr/bin/env bash\nprintf "%s:%s\\n" "$BUILD_MAX_PARALLELISM" "$BUILD_BUILDER"\n')
            wrapper.chmod(0o755)
            settings = root / '.env'
            settings.write_text('BUILD_MAX_PARALLELISM=2\nBUILD_BUILDER=from-env\n')
            env = {k: v for k, v in os.environ.items() if not k.startswith(('BUILD_', 'BUILDX_', 'DESIGNS', 'SHARED_DIR', 'DRY_RUN'))}
            env['ENV_FILE'] = str(settings)
            result = subprocess.run(['bash', str(root / 'runtime/start.sh'), 'build'], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '2:from-env\n')

    def test_named_builder_defaults_to_two(self):
        result, calls, config = self.run_setup(BUILD_BUILDER='my-builder')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('my-builder', result.stdout.splitlines())
        self.assertIn('max-parallelism = 2', config)

    def test_reuses_matching_builder_without_mutating_it(self):
        result, calls, _ = self.run_setup(BUILD_MAX_PARALLELISM='2', INSPECTION='Driver: docker-container\n > max-parallelism = 2\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(call[:2] == ['buildx', 'create'] for call in calls))

    def test_rejects_existing_incompatible_builder(self):
        for inspection in ('Driver: docker\n', 'Driver: docker-container\n > max-parallelism = 20\n'):
            with self.subTest(inspection=inspection):
                result, calls, _ = self.run_setup(BUILD_MAX_PARALLELISM='2', INSPECTION=inspection)
                self.assertEqual(result.returncode, 2)
                self.assertIn('left untouched', result.stderr)
                self.assertFalse(any(call[:2] == ['buildx', 'create'] for call in calls))

    def test_rejects_invalid_parallelism_before_docker(self):
        for value in ('0', '-1', '2.5', 'abc', '02', '2\n3'):
            with self.subTest(value=value):
                result, calls, _ = self.run_setup(BUILD_MAX_PARALLELISM=value)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(calls, [])

    def test_rejects_default_and_invalid_builder_names(self):
        for value in ('default', '--use', 'a b', 'a/b'):
            with self.subTest(value=value):
                result, calls, _ = self.run_setup(BUILD_BUILDER=value)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
