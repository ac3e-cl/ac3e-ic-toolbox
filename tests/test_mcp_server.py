"""Host-only tests; the MCP SDK is imported only by create_server()."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location('unic_mcp', ROOT / 'images/mcp/server.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.workspace = self.root / 'designs'
        self.workspace.mkdir()
        self.pdks = self.root / 'pdks'
        self.pdks.mkdir()
        (self.pdks / 'sky130A').mkdir()
        self.config = self.root / 'env.sh'
        self.config.write_text('echo config-noise\nexport PRIVATE_TOKEN=secret\n')
        self.module = load_module()
        self.backend = self.module.Backend(self.workspace, self.config, self.pdks)
        self.addCleanup(self.backend.close)

    def test_environment_is_filtered_and_pdk_listing_is_validated(self):
        status = self.backend.environment_status()
        self.assertNotIn('PRIVATE_TOKEN', str(status))
        self.assertEqual(status['workspace'], str(self.workspace))
        self.assertEqual(self.backend.list_pdks(), ['sky130A'])
        self.assertRaises(ValueError, self.backend.validate_pdk, '../pdks')

    def wait_job(self, job):
        import time
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            status = self.backend.job_status(job['job_id'])
            if status['state'] in ('succeeded', 'failed', 'cancelled', 'timed_out'):
                return status
            time.sleep(0.02)
        self.fail('job did not finish')

    def install_fake_tool(self, name, body):
        bindir = self.root / 'bin'
        bindir.mkdir(exist_ok=True)
        tool = bindir / name
        tool.write_text('#!/bin/sh\n' + body)
        tool.chmod(0o755)
        self.config.write_text('echo config-noise\nset_pdk() { export PDK="$1"; }\nexport PATH="' + str(bindir) + ':$PATH"\n')

    def test_simulation_runs_with_sourced_environment_and_isolated_output(self):
        self.install_fake_tool('ngspice', 'printf "%s\\n" "$@"\nprintf result > result.txt\n')
        (self.workspace / 'a ;$ net.cir').write_text('trusted netlist')
        job = self.backend.simulate_netlist('a ;$ net.cir', pdk='sky130A')
        self.assertEqual(self.wait_job(job)['state'], 'succeeded')
        logs = self.backend.job_logs(job['job_id'])
        self.assertIn('config-noise', logs['text'])
        self.assertIn(str(self.workspace / 'a ;$ net.cir'), logs['text'])
        artifacts = self.backend.list_artifacts(job['job_id'])
        self.assertIn('result.txt', [a['path'] for a in artifacts['artifacts']])
        self.assertEqual(self.backend.read_artifact(job['job_id'], 'result.txt')['text'], 'result')
        self.assertRaises(ValueError, self.backend.read_artifact, job['job_id'], '../../env.sh')
        self.assertRaises(ValueError, self.backend.simulate_netlist, 'a ;$ net.cir', 'bash')

    def test_log_open_failure_marks_job_failed_and_closes_pipe(self):
        import time
        from unittest.mock import patch
        (self.workspace / 'a.cir').write_text('x')
        for body in ('printf done\n', 'sleep 30 &\nwait\n'):
            with self.subTest(body=body):
                self.install_fake_tool('ngspice', body)
                started = time.monotonic()
                with patch.object(self.module, 'open', create=True,
                                  side_effect=OSError(28, 'No space left on device')):
                    job = self.backend.simulate_netlist('a.cir', timeout=4)
                    status = self.wait_job(job)
                self.assertLess(time.monotonic() - started, 2, 'reader failure waited for job timeout')
                self.assertEqual(status['state'], 'failed')
                self.assertIn('No space left on device', status['error'])
                self.assertIsNotNone(status['returncode'])
                process = self.backend.jobs[job['job_id']]['process']
                self.assertIsNotNone(process.poll())
                self.assertTrue(process.stdout.closed)

    def test_log_write_failure_promptly_kills_process_group(self):
        import time
        from unittest.mock import mock_open, patch
        self.install_fake_tool('ngspice', 'sleep 30 &\necho $! > child.pid\nhead -c 1000000 /dev/zero\nwait\n')
        (self.workspace / 'a.cir').write_text('x')
        for operation in ('write', 'flush'):
            with self.subTest(operation=operation):
                log_open = mock_open()
                getattr(log_open.return_value, operation).side_effect = OSError(28, 'No space left on device')
                started = time.monotonic()
                with patch.object(self.module, 'open', log_open, create=True):
                    job = self.backend.simulate_netlist('a.cir', timeout=4)
                    status = self.wait_job(job)
                self.assertLess(time.monotonic() - started, 2, 'reader failure waited for job timeout')
                self.assertEqual(status['state'], 'failed')
                self.assertIn('No space left on device', status['error'])
                self.assertIsNotNone(status['returncode'])
                process = self.backend.jobs[job['job_id']]['process']
                self.assertIsNotNone(process.poll())
                self.assertTrue(process.stdout.closed)
                pid = int((Path(job['output_dir']) / 'child.pid').read_text())
                stat = Path('/proc') / str(pid) / 'stat'
                if stat.exists():
                    self.assertEqual(stat.read_text().split()[2], 'Z')

    def test_timeout_cancel_concurrency_and_close(self):
        self.install_fake_tool('ngspice', 'sleep 30 &\nwait\n')
        (self.workspace / 'a.cir').write_text('x')
        first = self.backend.simulate_netlist('a.cir', timeout=0.2)
        second = self.backend.simulate_netlist('a.cir')
        self.assertRaises(RuntimeError, self.backend.simulate_netlist, 'a.cir')
        self.assertEqual(self.wait_job(first)['state'], 'timed_out')
        self.backend.cancel_job(second['job_id'])
        self.assertEqual(self.wait_job(second)['state'], 'cancelled')
        third = self.backend.simulate_netlist('a.cir')
        self.backend.close()
        self.assertEqual(self.backend.job_status(third['job_id'])['state'], 'cancelled')

    def test_output_root_symlink_is_rejected(self):
        self.backend.close()
        (self.workspace / '.unic-cass-mcp').symlink_to(self.root)
        self.assertRaises(ValueError, self.module.Backend, self.workspace, self.config, self.pdks)

    def test_script_runners_and_flow_use_fixed_argv(self):
        for tool in ('yosys', 'openroad', 'klayout', 'magic', 'librelane', 'Xyce'):
            self.install_fake_tool(tool, 'printf "%s\\n" "$@"\n')
        (self.workspace / 'trusted.script').write_text('x')
        for tool, expected in (('yosys', '-s'), ('openroad', '-exit'), ('klayout', '-b'), ('magic', '-dnull')):
            job = self.backend.run_script(tool, 'trusted.script', pdk='sky130A')
            self.assertEqual(self.wait_job(job)['state'], 'succeeded')
            self.assertIn(expected, self.backend.job_logs(job['job_id'])['text'])
        self.assertRaises(ValueError, self.backend.run_script, 'bash', 'trusted.script')
        flow = self.backend.start_flow('trusted.script', 'sky130A')
        self.assertEqual(self.wait_job(flow)['state'], 'succeeded')
        log = self.backend.job_logs(flow['job_id'])['text']
        self.assertNotIn('--run-dir', log)
        self.assertIn('--design-dir', log)
        for arg in ('--manual-pdk', '--pdk-root', str(self.pdks), '--pdk', 'sky130A'):
            self.assertIn(arg, log)
        self.assertIn('--jobs\n2\n', log)
        self.assertTrue(self.backend.environment_status()['tools']['yosys'])

    def test_log_pagination_limits_and_artifact_symlinks(self):
        self.install_fake_tool('ngspice', 'printf 0123456789\n')
        (self.workspace / 'a.cir').write_text('x')
        job = self.backend.simulate_netlist('a.cir')
        self.wait_job(job)
        root = Path(job['output_dir'])
        (root / 'escape').symlink_to(self.config)
        self.assertRaises(ValueError, self.backend.read_artifact, job['job_id'], 'escape')
        self.assertNotIn('escape', [a['path'] for a in self.backend.list_artifacts(job['job_id'])['artifacts']])
        page = self.backend.job_logs(job['job_id'], limit=3)
        self.assertEqual(page['next_offset'], 3)
        self.assertTrue(page['has_more'])
        self.assertRaises(ValueError, self.backend.job_logs, job['job_id'], 0, 65537)
        self.assertRaises(ValueError, self.backend.job_status, 'unknown')
        self.assertRaises(ValueError, self.backend.simulate_netlist, 'a.cir', timeout=float('nan'))

    def test_leader_exit_kills_descendant_and_logs_are_capped(self):
        self.install_fake_tool('ngspice', 'sleep 30 &\necho $! > child.pid\nhead -c 9000000 /dev/zero\n')
        (self.workspace / 'a.cir').write_text('x')
        job = self.backend.simulate_netlist('a.cir')
        status = self.wait_job(job)
        self.assertEqual(status['state'], 'succeeded')
        self.assertTrue(status['log_truncated'])
        self.assertEqual((Path(job['output_dir']) / 'output.log').stat().st_size, self.module.LOG_CAP)
        pid = int((Path(job['output_dir']) / 'child.pid').read_text())
        stat = Path('/proc') / str(pid) / 'stat'
        if stat.exists():
            self.assertEqual(stat.read_text().split()[2], 'Z')

    def test_main_uses_defaults_and_closes_after_stdio_eof(self):
        from unittest.mock import patch
        events = []
        class FakeBackend:
            def __init__(self, workspace, config, pdk_root):
                events.append((workspace, config, pdk_root))
            def close(self):
                events.append('closed')
        class FakeServer:
            def run(self, transport):
                events.append(transport)
        with patch.object(self.module, 'Backend', FakeBackend), patch.object(self.module, 'create_server', return_value=FakeServer()):
            self.module.main([])
        self.assertEqual(events, [('/foss/designs', '/opt/unic-cass/config/unic-cass-env.sh', '/opt/pdks'), 'stdio', 'closed'])

    def test_workspace_rejects_traversal_and_symlink_escape(self):
        (self.workspace / 'escape').symlink_to(self.root)
        for path in ('../env.sh', '/etc/passwd', 'escape/env.sh', '.unic-cass-mcp/x'):
            with self.subTest(path=path):
                self.assertRaises(ValueError, self.backend.input_path, path)

    def test_explicit_job_pdk_wins_over_project_initialization(self):
        self.install_fake_tool('ngspice', 'printf "selected=%s\\n" "$PDK"\n')
        with self.config.open('a') as config:
            config.write('export PDK=project-default\nset_pdk() { export PDK="$1"; }\n')
        (self.workspace / 'a.cir').write_text('x')
        job = self.backend.simulate_netlist('a.cir', pdk='sky130A')
        self.assertEqual(self.wait_job(job)['state'], 'succeeded')
        self.assertIn('selected=sky130A', self.backend.job_logs(job['job_id'])['text'])


if __name__ == '__main__':
    unittest.main()
