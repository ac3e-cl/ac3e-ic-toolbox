"""Contracts for isolated, prebuilt LibreLane template environments."""
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'images/librelane/librelane-template'


class LibreLaneTemplates(unittest.TestCase):
    def test_documented_template_commands_use_retained_keys(self):
        docs = (ROOT / 'docs/librelane-templates.md').read_text()
        keys = re.findall(r'^librelane-template (?:init|run) (\w+) ', docs, re.M)
        self.assertEqual(set(keys), {'ihp', 'gf'})
        self.assertNotIn('all three installed', docs.lower())
        self.assertIn('not validation of the current no-SKY image', docs)

    def test_installer_accepts_only_retained_template_pins(self):
        installer = (ROOT / 'images/librelane/install.sh').read_text()
        match = re.search(r"rows_text=\$\(python3 - .*? <<'PY'\n(.*?)\nPY", installer, re.S)
        self.assertIsNotNone(match)
        assert match is not None
        validator = match[1]
        result = subprocess.run(['python3', '-', str(ROOT / 'manifest.json')],
                                input=validator, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual({row.split('\t')[0] for row in result.stdout.splitlines()}, {'ihp', 'gf'})
        self.assertIn('[[ ${#rows[@]} == 2 ]]', installer)
        self.assertNotIn('sky', installer.lower())

    def test_only_retained_templates_are_pinned(self):
        pins = json.loads((ROOT / 'manifest.json').read_text())['librelaneTemplates']
        self.assertEqual(set(pins), {'ihp', 'gf'})
        baseline = json.loads(subprocess.check_output(
            ['git', 'show', 'HEAD:manifest.json'], cwd=ROOT, text=True))
        for key in ('ihp', 'gf'):
            self.assertEqual(pins[key], baseline['librelaneTemplates'][key])

    def test_removed_template_is_rejected_even_if_stale_source_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'src/sky').mkdir(parents=True)
            project = base / 'project'
            result = subprocess.run(['bash', str(RUNNER), 'init', 'sky', str(project)],
                                    env=dict(os.environ, LIBRELANE_TEMPLATES_ROOT=tmp),
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertFalse(project.exists())
            self.assertIn('{ihp|gf}', result.stderr)

    def test_gf_full_flow_is_manual_only(self):
        helper = (ROOT / 'tests/helpers/librelane-template-test.sh').read_text()
        self.assertNotIn('--skip OpenROAD.IRDropReport', helper)
        self.assertNotIn('mode=${4:', helper)
        regular = (ROOT / 'tests/pdk/librelane-template-gf.sh').read_text()
        self.assertIn('complete flow', regular)
        ir = ROOT / 'tests/pdk/librelane-template-gf-irdrop.sh'
        self.assertFalse(ir.exists())
        exclusions = json.loads((ROOT / 'tests/exclusions.json').read_text())['long_running']
        self.assertNotIn('pdk/librelane-template-gf-irdrop.sh', exclusions)
        self.assertIn('pdk/librelane-template-gf.sh', exclusions)

    def test_failed_template_tests_report_the_evidence_directory(self):
        for key in ['ihp', 'gf']:
            with self.subTest(key=key), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                (base / 'pdk').mkdir()
                (base / 'bin').mkdir()
                script = base / 'pdk' / f'librelane-template-{key}.sh'
                script.write_text((ROOT / 'tests/pdk' / script.name).read_text())
                (base / 'common.sh').write_text((ROOT / 'tests/common.sh').read_text())
                fake = base / 'bin/librelane-template'
                fake.write_text('#!/usr/bin/env bash\nif [[ "$1" == init ]]; then mkdir -p "$3"; else exit 17; fi\n')
                fake.chmod(0o755)
                env = dict(os.environ, PATH=str(base / 'bin') + os.pathsep + os.environ['PATH'])
                result = subprocess.run(['bash', str(script)], env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 17)
                self.assertIn('/project/evidence', result.stdout + result.stderr)

    def test_init_copies_pinned_source_without_overwriting_existing_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / 'src/gf'
            source.mkdir(parents=True)
            (source / 'flake.lock').write_text('upstream lock')
            project = base / 'new project'
            env = dict(os.environ, LIBRELANE_TEMPLATES_ROOT=tmp)
            args = ['bash', str(RUNNER), 'init', 'gf', str(project)]
            result = subprocess.run(args, env=env, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((project / 'flake.lock').read_text(), 'upstream lock')
            (project / 'flake.lock').write_text('user change')
            self.assertNotEqual(subprocess.run(args, env=env, capture_output=True).returncode, 0)
            self.assertEqual((project / 'flake.lock').read_text(), 'user change')

    def test_run_discards_toolbox_environment_and_preserves_arguments(self):
        self.assertTrue(RUNNER.is_file(), 'template launcher is not installed yet')
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'activate').mkdir()
            (base / 'activate/ihp.sh').write_text(
                'export TEMPLATE_ACTIVATED=yes\n'
                'export PDK_ROOT=/wrong\n'
                'shellHook="export PDK=wrong"\n')
            project = base / 'project with spaces'
            project.mkdir()
            fake = base / 'inspect-env'
            fake.write_text('#!/usr/bin/python3\nimport json, os, sys\n'
                            'print(json.dumps({"args": sys.argv[1:], "env": dict(os.environ)}))\n')
            fake.chmod(0o755)
            env = dict(os.environ, LIBRELANE_TEMPLATES_ROOT=tmp,
                       PDK_ROOT='/opt/pdks', PDK='gf180mcuD',
                       STD_CELL_LIBRARY='wrong', PYTHONPATH='/wrong',
                       LD_LIBRARY_PATH='/wrong', BASH_ENV='/nonexistent')
            result = subprocess.run(['bash', str(RUNNER), 'run', 'ihp', str(project),
                                     str(fake), 'printf', '%s', 'an argument with spaces'],
                                    env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            for name in ['STD_CELL_LIBRARY', 'BASH_ENV',
                         'PYTHONPATH', 'LD_LIBRARY_PATH']:
                self.assertNotIn(name, data['env'])
            self.assertEqual(data['env']['PDK_ROOT'], str(base / 'pdks/ihp'))
            self.assertEqual(data['env']['PDK'], 'ihp-sg13g2')
            self.assertEqual(data['env']['TEMPLATE_ACTIVATED'], 'yes')
            self.assertEqual(data['args'][-3:], ['printf', '%s', 'an argument with spaces'])


if __name__ == '__main__':
    unittest.main()
