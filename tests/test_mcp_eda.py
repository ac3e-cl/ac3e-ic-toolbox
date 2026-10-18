"""Host tests. Executable fixtures exercise plumbing, NOT real EDA validation."""
import ast
import importlib.util
import inspect
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_eda():
    path = ROOT / 'images/mcp/eda.py'
    if not path.is_file():
        raise AssertionError('EDAMixin implementation is missing')
    spec = importlib.util.spec_from_file_location('eda_under_test', path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CatalogTests(unittest.TestCase):
    def test_catalog_covers_repository_inventory_with_honest_exclusions(self):
        module = load_eda()
        source = (ROOT / 'tests/inventory/tools.sh').read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
        commands = next(ast.literal_eval(node.value) for node in ast.parse(source).body
                        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'commands' for t in node.targets))
        catalog = module.EDAMixin().tool_catalog()
        entries = {item['name']: item for item in catalog['tools']}
        self.assertTrue(set(commands.values()) <= entries.keys())
        self.assertEqual(set(module.TOOLS), entries.keys())
        self.assertIn('vvp', entries)
        self.assertEqual(entries['mcy']['status'], 'excluded')
        self.assertEqual(entries['Xyce']['status'], 'excluded')
        self.assertIn('disabled', entries['mcy']['notes'])
        self.assertEqual({r['name'] for r in catalog['resources']}, {'open_pdks', 'ihp-sg13g2', 'OpenROAD-flow-scripts'})
        for entry in entries.values():
            self.assertTrue(entry['description'])
            self.assertTrue(entry['capabilities'])
            self.assertTrue(entry['examples'])
            self.assertIsNone(entry['available'])
            self.assertTrue(all(example[0] == entry['name'] for example in entry['examples']))
        self.assertIsInstance(module.EDA_METHODS, tuple)
        self.assertNotIn('run_script', module.EDA_METHODS)
        for name in module.EDA_METHODS:
            self.assertTrue(callable(getattr(module.EDAMixin, name)))
            signature = inspect.signature(getattr(module.EDAMixin, name))
            self.assertIsNot(signature.return_annotation, inspect.Signature.empty)
            for parameter in signature.parameters.values():
                if parameter.name != 'self':
                    self.assertIsNot(parameter.annotation, inspect.Signature.empty)
        catalog['tools'][0]['examples'][0].append('TEST_MUTATION_SENTINEL')
        self.assertNotIn('TEST_MUTATION_SENTINEL', str(module.EDAMixin().tool_catalog()))


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.module = load_eda()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / 'designs'
        self.workspace.mkdir()
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.config = self.root / 'config.sh'
        self.config.write_text('export PATH=' + str(self.bin) + ':"$PATH"\nset_pdk() { export PDK="$1"; }\n')
        outer = self

        class FixtureBackend(self.module.EDAMixin):
            """Real subprocess harness; fixture programs do not implement EDA."""
            workspace = outer.workspace
            config = outer.config

            def input_path(self, value):
                path = self.filesystem_path(value)
                if not path.is_file():
                    raise ValueError('input must be a file')
                return path

            def filesystem_path(self, value):
                path = (self.workspace / value).resolve()
                if '..' in Path(value).parts or not path.is_relative_to(self.workspace):
                    raise ValueError('outside workspace')
                return path

            def validate_pdk(self, value):
                if value != 'sky130A':
                    raise ValueError('unknown PDK')
                return value

            def _submit(self, argv, pdk, timeout, cwd=None):
                output = Path(tempfile.mkdtemp(dir=outer.root))
                run = 'source "$1"; selected=$2; shift 2; if [[ -n "$selected" ]]; then set_pdk "$selected"; fi; exec "$@"'
                try:
                    process = subprocess.run(['bash', '--noprofile', '--norc', '-c', run, 'fixture', str(self.config), pdk, *argv],
                                             cwd=cwd or output, env={k: v for k, v in os.environ.items() if k != 'BASH_ENV'},
                                             stdin=subprocess.DEVNULL, capture_output=True, timeout=timeout)
                except subprocess.TimeoutExpired:
                    return {'state': 'timed_out', 'output_dir': str(output)}
                return {'state': 'succeeded' if process.returncode == 0 else 'failed',
                        'returncode': process.returncode, 'stdout': process.stdout.decode(),
                        'output_dir': str(output)}

        self.backend = FixtureBackend()

    def fixture_executable(self, name, body=None):
        executable = self.bin / name
        executable.write_text('#!' + sys.executable + '\n' + (body or
                              'import os, sys, json\nfrom pathlib import Path\n'
                              'data = {"argv": sys.argv[1:], "cwd": os.getcwd(), "pdk": os.getenv("PDK")}\n'
                              'Path("fixture-result.json").write_text(json.dumps(data))\nprint(json.dumps(data))\n'))
        executable.chmod(0o755)

    def test_run_tool_preserves_literal_argv_and_uses_isolated_output(self):
        self.assertTrue(hasattr(self.backend, 'run_tool'), 'generic tool execution is missing')
        self.fixture_executable('iverilog')
        arguments = ['', 'a b', '; touch INJECTION', '$(touch INJECTION)', '\n', '*', 'a"b', 'á']
        job = self.backend.run_tool('iverilog', arguments, pdk='sky130A')
        self.assertEqual(job['state'], 'succeeded')
        result = json.loads(job['stdout'])
        self.assertEqual(result['argv'], arguments)
        self.assertEqual(result['cwd'], job['output_dir'])
        self.assertEqual(result['pdk'], 'sky130A')
        self.assertFalse((Path(job['output_dir']) / 'INJECTION').exists())
        self.assertTrue((Path(job['output_dir']) / 'fixture-result.json').is_file())
        self.assertFalse((self.workspace / 'fixture-result.json').exists())

    def test_invalid_requests_are_rejected_before_submission(self):
        invalid = [
            {'tool': 'bash'}, {'tool': '/usr/bin/iverilog'}, {'tool': 'Iverilog'},
            {'tool': None}, {'tool': 'iverilog\x00'}, {'arguments': '-v'},
            {'arguments': ('-v',)}, {'arguments': [1]}, {'arguments': ['a\x00b']},
            {'arguments': ['x' * 32769]}, {'arguments': ['é' * 16385]}, {'arguments': ['x'] * 1025},
            {'arguments': ['x' * 32768] * 9}, {'arguments': ['\ud800']},
            {'timeout': 0}, {'timeout': -1}, {'timeout': float('nan')},
            {'timeout': float('inf')}, {'timeout': 86401}, {'timeout': True},
            {'timeout': '3'}, {'pdk': None}, {'pdk': '../bad'}, {'pdk': '\x00'},
            {'cwd': None}, {'cwd': '\x00'}, {'cwd': '../'},
        ]
        def forbidden(*args, **kwargs):
            self.fail('invalid request reached job submission')
        self.backend._submit = forbidden
        for overrides in invalid:
            with self.subTest(overrides=str(overrides)[:100]):
                request = dict(tool='iverilog', arguments=[])
                request.update(overrides)
                self.assertRaises(ValueError, self.backend.run_tool, **request)

    def test_explicit_cwd_requires_a_policy_approved_directory(self):
        self.fixture_executable('iverilog')
        project = self.workspace / 'project space'
        project.mkdir()
        job = self.backend.run_tool('iverilog', ['relative.v'], cwd='project space')
        self.assertEqual(json.loads(job['stdout'])['cwd'], str(project))
        self.assertTrue((project / 'fixture-result.json').is_file())
        self.assertFalse((Path(job['output_dir']) / 'fixture-result.json').exists())
        (self.workspace / 'file').write_text('file')
        for cwd in ('file', 'absent', '../', str(self.root)):
            with self.subTest(cwd=cwd):
                self.assertRaises(ValueError, self.backend.run_tool, 'iverilog', [], cwd=cwd)

    def test_failed_and_timed_out_executables_are_not_reported_successful(self):
        self.fixture_executable('iverilog', 'raise SystemExit(7)\n')
        result = self.backend.run_tool('iverilog', [])
        self.assertEqual((result['state'], result['returncode']), ('failed', 7))
        self.fixture_executable('iverilog', 'import time\ntime.sleep(10)\n')
        self.assertEqual(self.backend.run_tool('iverilog', [], timeout=0.05)['state'], 'timed_out')

    def test_xschem_netlisting_uses_headless_cli_and_validated_rcfile(self):
        self.assertTrue(hasattr(self.backend, 'xschem_netlist'), 'Xschem netlisting is missing')
        self.fixture_executable('xschem')
        schematic = self.workspace / 'schematic ;$.sch'
        schematic.write_text('fixture input, not an actual schematic')
        rcfile = self.workspace / 'xschemrc'
        rcfile.write_text('fixture configuration')
        job = self.backend.xschem_netlist(schematic.name, rcfile=rcfile.name)
        self.assertEqual(json.loads(job['stdout'])['argv'],
                         ['-n', '-q', '-x', '-o', '.', '--rcfile', str(rcfile), str(schematic)])
        self.assertRaises(ValueError, self.backend.xschem_netlist, 'missing.sch')
        self.assertRaises(ValueError, self.backend.xschem_netlist, schematic.name, rcfile='missing')

    def test_netgen_lvs_passes_tcl_list_specs_and_reports_process_status_only(self):
        self.assertTrue(hasattr(self.backend, 'netgen_lvs'), 'Netgen LVS is missing')
        self.fixture_executable('netgen')
        for name in ('a.spice', 'b.spice', 'setup.tcl'):
            (self.workspace / name).write_text('fixture input')
        job = self.backend.netgen_lvs('a.spice', 'top', 'b.spice', 'top', setup='setup.tcl')
        self.assertEqual(json.loads(job['stdout'])['argv'],
                         ['-batch', 'lvs', str(self.workspace / 'a.spice') + ' top',
                          str(self.workspace / 'b.spice') + ' top', str(self.workspace / 'setup.tcl'), 'lvs.log'])
        job = self.backend.netgen_lvs('a.spice', 'top', 'b.spice', 'top')
        self.assertEqual(json.loads(job['stdout'])['argv'][-2:], ['nosetup', 'lvs.log'])
        special = 'a space{[\\;$.spice'
        (self.workspace / special).write_text('fixture input')
        job = self.backend.netgen_lvs(special, 'top space', 'b.spice', 'top')
        specification = json.loads(job['stdout'])['argv'][2]
        self.assertIn('a\\ space\\{\\[\\\\\\;\\$.spice', specification)
        self.assertTrue(specification.endswith(' top\\ space'))
        self.assertRaises(ValueError, self.backend.netgen_lvs, 'a.spice', '', 'b.spice', 'top')

    def test_verilator_lint_validates_sources_and_preserves_options(self):
        self.assertTrue(hasattr(self.backend, 'lint_verilog'), 'Verilator lint is missing')
        self.fixture_executable('verilator')
        (self.workspace / 'design.sv').write_text('fixture RTL')
        job = self.backend.lint_verilog(['design.sv'], top='top', arguments=['-Wall', '-Iincludes space'])
        self.assertEqual(json.loads(job['stdout'])['argv'],
                         ['--lint-only', '--top-module', 'top', '-Wall', '-Iincludes space', str(self.workspace / 'design.sv')])
        for sources in ([], 'design.sv', ['absent'], [1]):
            self.assertRaises(ValueError, self.backend.lint_verilog, sources)
        self.assertRaises(ValueError, self.backend.lint_verilog, ['design.sv'], arguments=['bad\x00'])

    def test_iverilog_compilation_builds_explicit_output_and_language(self):
        self.assertTrue(hasattr(self.backend, 'compile_verilog'), 'Icarus compilation is missing')
        self.fixture_executable('iverilog')
        (self.workspace / 'tb.sv').write_text('fixture RTL')
        job = self.backend.compile_verilog(['tb.sv'], top='tb', arguments=['-DVALUE=hello world'])
        self.assertEqual(json.loads(job['stdout'])['argv'], ['-g2012', '-o', 'simulation.vvp', '-s', 'tb',
                         '-DVALUE=hello world', str(self.workspace / 'tb.sv')])
        for output in ('../escape', '/escape', '-option', '', '.', 'a/b', '\x00'):
            self.assertRaises(ValueError, self.backend.compile_verilog, ['tb.sv'], output=output)
        self.assertRaises(ValueError, self.backend.compile_verilog, ['tb.sv'], standard='madeup')

    def test_vvp_accepts_generated_files_via_filesystem_policy(self):
        self.assertTrue(hasattr(self.backend, 'run_vvp'), 'VVP simulation is missing')
        self.fixture_executable('vvp')
        directory = self.workspace / '.ac3e-ic-toolbox-mcp' / 'previous-job'
        directory.mkdir(parents=True)
        program = directory / 'simulation.vvp'
        program.write_text('fixture program, not real bytecode')
        job = self.backend.run_vvp(str(program), arguments=['+VALUE=a b', '+trace'])
        self.assertEqual(json.loads(job['stdout'])['argv'], [str(program), '+VALUE=a b', '+trace'])
        self.assertRaises(ValueError, self.backend.run_vvp, str(directory))
        self.assertRaises(ValueError, self.backend.run_vvp, 'absent')

    def test_openvaf_compiles_to_explicit_osdi_output(self):
        self.assertTrue(hasattr(self.backend, 'compile_veriloga'), 'OpenVAF compilation is missing')
        self.fixture_executable('openvaf')
        (self.workspace / 'model.va').write_text('fixture model')
        job = self.backend.compile_veriloga('model.va', arguments=['-I', 'includes'])
        self.assertEqual(json.loads(job['stdout'])['argv'],
                         [str(self.workspace / 'model.va'), '-o', 'model.osdi', '-I', 'includes'])
        self.assertRaises(ValueError, self.backend.compile_veriloga, 'model.va', output='../escape')

    def test_formal_frontends_use_real_distinct_cli_contracts(self):
        self.assertTrue(hasattr(self.backend, 'run_formal'), 'formal frontend execution is missing')
        for tool in ('eqy', 'sby', 'mcy'):
            self.fixture_executable(tool)
        (self.workspace / 'proof.sby').write_text('fixture proof config')
        for tool in ('eqy', 'sby'):
            job = self.backend.run_formal(tool, 'proof.sby', arguments=['task'])
            self.assertEqual(json.loads(job['stdout'])['argv'],
                             ['-d', 'formal', str(self.workspace / 'proof.sby'), 'task'])
        job = self.backend.run_formal('mcy', cwd='.')
        self.assertEqual(json.loads(job['stdout'])['argv'], ['status'])
        job = self.backend.run_formal('mcy', arguments=['run', '-j', '2'], cwd='.')
        self.assertEqual(json.loads(job['stdout'])['argv'], ['run', '-j', '2'])
        for tool, config, cwd in (('bash', '', ''), ('mcy', 'proof.sby', '.'),
                                   ('mcy', '', ''), ('sby', '', '')):
            self.assertRaises(ValueError, self.backend.run_formal, tool, config, cwd=cwd)

    def test_trusted_script_frontends_have_explicit_cli_not_a_generic_shell(self):
        self.assertTrue(hasattr(self.backend, 'run_tool_script'), 'additional tool scripts are missing')
        script = self.workspace / 'trusted ;$.tcl'
        script.write_text('fixture script')
        expected = {'netgen': ['-batch', 'source', str(script)],
                    'xschem': ['-q', '-x', '--script', str(script)],
                    'gnucap': ['-b', str(script)], 'sta': ['-exit', str(script)]}
        for tool, argv in expected.items():
            with self.subTest(tool=tool):
                self.fixture_executable(tool)
                job = self.backend.run_tool_script(tool, script.name)
                self.assertEqual(json.loads(job['stdout'])['argv'], argv)
        self.assertRaises(ValueError, self.backend.run_tool_script, 'bash', script.name)

    def test_actual_backend_jobs_execute_fixture_tools_with_both_cwd_modes(self):
        spec = importlib.util.spec_from_file_location('eda_integration_server', ROOT / 'images/mcp/server.py')
        assert spec is not None and spec.loader is not None
        server = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(server)

        class ComposedBackend(self.module.EDAMixin, server.Backend):
            pass

        pdks = self.root / 'pdks'
        (pdks / 'sky130A').mkdir(parents=True)
        backend = ComposedBackend(self.workspace, self.config, pdks)
        self.addCleanup(backend.close)
        self.fixture_executable('iverilog')
        for cwd in ('', '.'):
            with self.subTest(cwd=cwd):
                job = backend.run_tool('iverilog', ['literal ;$ argument'], pdk='sky130A', cwd=cwd)
                deadline = time.monotonic() + 5
                status = job
                while time.monotonic() < deadline:
                    status = backend.job_status(job['job_id'])
                    if status['state'] not in ('queued', 'running'):
                        break
                    time.sleep(0.01)
                self.assertEqual(status['state'], 'succeeded', status)
                result = json.loads(backend.job_logs(job['job_id'])['text'])
                self.assertEqual(result['argv'], ['literal ;$ argument'])
                self.assertEqual(result['pdk'], 'sky130A')
                self.assertEqual(result['cwd'], str(self.workspace) if cwd else job['output_dir'])

    def test_all_catalog_executables_allow_exact_argv_within_bounds(self):
        submitted = []
        self.backend._submit = lambda argv, pdk, timeout, cwd=None: submitted.append(argv) or {'queued': True}
        for name in self.module.TOOLS:
            self.assertEqual(self.backend.run_tool(name, ['--help']), {'queued': True})
            self.assertEqual(submitted[-1], [name, '--help'])
        self.backend.run_tool('iverilog', ['é' * 16384])
        self.backend.run_tool('iverilog', [''] * 1024)


if __name__ == '__main__':
    unittest.main()
