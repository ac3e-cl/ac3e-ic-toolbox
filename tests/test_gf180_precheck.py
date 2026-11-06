"""Host fixtures exercise the real launcher; they do not certify EDA signoff."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / 'images/librelane/gf180-precheck'


class PrecheckLauncher(unittest.TestCase):
    def test_help_succeeds_without_installed_resources(self):
        result = subprocess.run(['bash', str(LAUNCHER), '--help'], text=True, capture_output=True,
                                env=dict(os.environ, LIBRELANE_TEMPLATES_ROOT='/nonexistent'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--input', result.stdout)

    def test_offline_activation_arguments_environment_and_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / 'project with spaces'
            project.mkdir()
            (project / 'input with spaces.oas').write_bytes(b'fixture')
            (base / 'src/gf-precheck').mkdir(parents=True)
            (base / 'pdks/gf-precheck/gf180mcuD').mkdir(parents=True)
            (base / 'activate').mkdir()
            (base / 'bin').mkdir()
            # These network/build commands must never run, even for a failed check.
            for command in ['nix', 'git', 'ciel', 'make']:
                script = base / 'bin' / command
                script.write_text('#!/bin/sh\necho runtime-download-forbidden >&2\nexit 99\n')
                script.chmod(0o755)
            (base / 'activate/gf-precheck.sh').write_text(
                f'export PATH="{base}/bin:/usr/bin:/bin"\n'
                'export PDK_ROOT=/incorrect\nexport PDK=ihp-sg13g2\n'
                'shellHook="export PDK=incorrect"\n')
            (base / 'src/gf-precheck/flake.lock').write_text('unchanged upstream lock')
            (base / 'src/gf-precheck/precheck.py').write_text(
                'import json, os, sys\n'
                'print(json.dumps({"args":sys.argv[1:], "env":dict(os.environ), "cwd":os.getcwd()}))\n'
                'sys.exit(17 if "--cob" in sys.argv else 0)\n')
            env = dict(os.environ, LIBRELANE_TEMPLATES_ROOT=tmp, PDK='ihp-sg13g2',
                       PDK_ROOT='/opt/pdks', STD_CELL_LIBRARY='bad', PYTHONPATH='/bad',
                       PYTHONHOME='/bad', LD_LIBRARY_PATH='/bad', BASH_ENV='/nonexistent',
                       USER='12345', HOME=str(project))
            args = ['bash', str(LAUNCHER), str(project), '--input', 'input with spaces.oas',
                    '--output', 'checked layout.oas', '--id', 'DEADBEEF', '--slot', '1x1',
                    '--top', 'top with spaces', '--run-tag', 'fixture']
            for extra, expected in [([], 0), (['--cob'], 17)]:
                result = subprocess.run(args + extra, env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, expected, result.stderr)
                data = json.loads(result.stdout)
                self.assertEqual(data['cwd'], str(project))
                self.assertEqual(data['env']['PDK_ROOT'], str(base / 'pdks/gf-precheck'))
                self.assertEqual(data['env']['PDK'], 'gf180mcuD')
                self.assertEqual(data['env']['HOME'], str(project))
                self.assertEqual(data['env']['USER'], '12345')
                for key in ['STD_CELL_LIBRARY', 'PYTHONPATH', 'PYTHONHOME', 'LD_LIBRARY_PATH', 'BASH_ENV']:
                    self.assertNotIn(key, data['env'])
                self.assertIn('input with spaces.oas', data['args'])
                self.assertIn('top with spaces', data['args'])
                self.assertEqual(data['args'][:6], ['--dir', str(project), '--threads', '1', '--workers', '1'])
                self.assertEqual((base / 'src/gf-precheck/flake.lock').read_text(), 'unchanged upstream lock')
            for extra in [['--dir', '/outside'], ['--skip', 'Magic.DRC'], ['--threads', 'max']]:
                with self.subTest(extra=extra):
                    result = subprocess.run(args + extra, env=env, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 2)
                    self.assertNotIn('"args"', result.stdout)
            for output in ['../escape.oas', 'input with spaces.oas']:
                with self.subTest(output=output):
                    invalid = args.copy()
                    invalid[invalid.index('--output') + 1] = output
                    result = subprocess.run(invalid, env=env, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 2)
                    self.assertNotIn('"args"', result.stdout)
            for tag in ['../../outside-project', '/absolute', '..', '.', 'nested/run']:
                with self.subTest(tag=tag):
                    invalid = args.copy()
                    invalid[invalid.index('--run-tag') + 1] = tag
                    result = subprocess.run(invalid, env=env, text=True, capture_output=True)
                    self.assertEqual(result.returncode, 2)
                    self.assertNotIn('"args"', result.stdout)
            outside = base / 'outside'
            outside.mkdir()
            (project / 'runs').symlink_to(outside, target_is_directory=True)
            result = subprocess.run(args, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            (project / 'runs').unlink()
            (project / 'runs').mkdir()
            (project / 'runs/fixture').symlink_to(outside, target_is_directory=True)
            result = subprocess.run(args, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            (base / 'activate/gf-precheck.sh').unlink()
            result = subprocess.run(args, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertIn('Missing prebuilt', result.stderr)


class PrecheckInstallation(unittest.TestCase):
    def test_installer_materializes_separate_profile_and_all_libraries(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / 'upstream'
            source.mkdir()
            pins = dict(url=str(source), version='1.7.4', commit='0' * 40,
                        librelaneCommit='1' * 40, pdk='gf180mcuD', pdkCommit='2' * 40,
                        cielVersion='3.1.0', cielCommit='3' * 40)
            lock = {'nodes': {'librelane': {'locked': {'rev': pins['librelaneCommit']},
                                          'inputs': {'ciel': 'ciel'}},
                              'ciel': {'locked': {'rev': pins['cielCommit']},
                                       'original': {'ref': '3.1.0'}}}}
            lock_text = json.dumps(lock)
            (source / 'flake.lock').write_text(lock_text)
            (source / 'Makefile').write_text('PDK_COMMIT ?= ' + pins['pdkCommit'] + '\n')
            for args in [['init', '-q'], ['add', '.'], ['-c', 'user.name=Fixture', '-c',
                         'user.email=fixture@invalid', 'commit', '-qm', 'fixture']]:
                subprocess.run(['git', '-C', str(source)] + args, check=True, capture_output=True)
            pins['commit'] = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            manifest = base / 'manifest.json'
            manifest.write_text(json.dumps({'librelanePrechecks': {'gf': pins}}))
            tools = base / 'bin'
            tools.mkdir()
            log = base / 'commands.jsonl'
            # Only the external Nix/Ciel boundary is a fixture; clone, validation,
            # activation, shell sanitization and lock checks execute for real.
            nix = tools / 'nix'
            nix.write_text('#!/usr/bin/python3\nimport json, sys\n'
                           f'with open({str(log)!r}, "a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\n'
                           'if sys.argv[1] == "print-dev-env":\n'
                           f' print("export PATH={tools}:/usr/bin:/bin")\n')
            nix.chmod(0o755)
            ciel = tools / 'ciel'
            ciel.write_text('#!/usr/bin/python3\nimport json, os, pathlib, sys\n'
                            f'with open({str(log)!r}, "a") as f: f.write(json.dumps(["ciel"]+sys.argv[1:])+"\\n")\n'
                            'if sys.argv[1] == "--version": print("ciel, version 3.1.0")\n'
                            'else:\n'
                            ' assert "PYTHONPATH" not in os.environ\n'
                            ' root=pathlib.Path(sys.argv[sys.argv.index("--pdk-root")+1])\n'
                            ' (root/"gf180mcuD").mkdir(parents=True)\n')
            ciel.chmod(0o755)
            root = base / 'installed'
            env = dict(os.environ, PATH=str(tools) + ':/usr/bin:/bin',
                       LIBRELANE_TEMPLATES_ROOT=str(root), MAX_BUILD_JOBS='3', PYTHONPATH='/wrong')
            result = subprocess.run(['bash', str(ROOT / 'images/librelane/install-precheck.sh'), str(manifest)],
                                    env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            commands = [json.loads(line) for line in log.read_text().splitlines()]
            develop = next(row for row in commands if row[0] == 'develop')
            self.assertIn('--no-update-lock-file', develop)
            self.assertIn(str(root / 'profiles/gf-precheck'), develop)
            self.assertEqual(develop[develop.index('--cores') + 1], '3')
            self.assertIn(['ciel', 'enable', pins['pdkCommit'], '--pdk-root', str(root / 'pdks/gf-precheck'),
                           '--pdk', 'gf180mcuD', '--include-libraries', 'all'], commands)
            self.assertEqual((root / 'src/gf-precheck/flake.lock').read_text(), lock_text)
            self.assertTrue((root / 'activate/gf-precheck.sh').is_file())
            self.assertTrue((root / 'metadata/gf-precheck.txt').is_file())

    def test_pins_validator_checks_private_lock_and_rejects_mismatches(self):
        validator = ROOT / 'images/librelane/precheck-pins.py'
        pins = dict(url='https://github.com/wafer-space/gf180mcu-precheck', version='1.7.4',
                    commit='9b4e7dab6af073d02b81ecc368069540d2f67db9',
                    librelaneCommit='99148a9c1e648cdfdb9d7b772481af32e0dfbe8b',
                    pdk='gf180mcuD', pdkCommit='792ef67037d74c8c51811eab3ce23cf793491296',
                    cielVersion='3.1.0', cielCommit='e180507a4190462d65cdded4448eb4f7bd2f30fa')
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            manifest = base / 'manifest.json'
            manifest.write_text(json.dumps({'librelanePrechecks': {'gf': pins}}))
            lock = {'nodes': {'librelane': {'locked': {'rev': pins['librelaneCommit']},
                                          'inputs': {'ciel': 'ciel'}},
                              'ciel': {'locked': {'rev': pins['cielCommit']},
                                       'original': {'ref': pins['cielVersion']}}}}
            (base / 'flake.lock').write_text(json.dumps(lock))
            (base / 'Makefile').write_text('PDK_COMMIT ?= ' + pins['pdkCommit'] + '\n')
            command = ['python3', str(validator), str(manifest), str(base)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip().split('\t'), [pins[k] for k in
                             ['url', 'commit', 'librelaneCommit', 'pdkCommit', 'cielVersion', 'cielCommit']])
            for field in ['librelaneCommit', 'pdkCommit', 'cielCommit']:
                with self.subTest(field=field):
                    changed = dict(pins, **{field: '0' * 40})
                    manifest.write_text(json.dumps({'librelanePrechecks': {'gf': changed}}))
                    self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            manifest.write_text(json.dumps({'librelanePrechecks': {'gf': dict(pins, commit='bad')}}))
            self.assertNotEqual(subprocess.run(command[:3], capture_output=True).returncode, 0)


if __name__ == '__main__':
    unittest.main()
