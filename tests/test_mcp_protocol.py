"""Opt-in end-to-end stdio test, including a real ngspice job.

Set MCP_TEST_COMMAND to a JSON argv array for the installed launcher and
MCP_TEST_WORKSPACE to its host-mounted design directory. Run with the MCP venv.
The test never starts or changes containers; its caller owns their lifecycle.
"""
import asyncio
import json
import os
import unittest
import uuid
from pathlib import Path


@unittest.skipUnless(os.environ.get('MCP_TEST_COMMAND'), 'Set MCP_TEST_COMMAND for live MCP integration')
class MCPProtocolTests(unittest.TestCase):
    def test_discovery_and_real_simulation(self):
        asyncio.run(self.exercise())

    async def exercise(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        argv = json.loads(os.environ['MCP_TEST_COMMAND'])
        workspace = Path(os.environ['MCP_TEST_WORKSPACE'])
        filename = f'mcp-smoke-{uuid.uuid4().hex}.spice'
        netlist = workspace / filename
        netlist.write_text('MCP voltage divider\nV1 in 0 DC 1\nR1 in out 1k\nR2 out 0 1k\n.control\nop\nprint v(out)\n.endc\n.end\n')
        try:
            async with stdio_client(StdioServerParameters(command=argv[0], args=argv[1:])) as (reader, writer), ClientSession(reader, writer) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    names = {tool.name for tool in tools.tools}
                    self.assertTrue({'environment_status', 'list_pdks', 'simulate_netlist',
                                     'run_script', 'start_flow', 'job_status', 'job_logs',
                                     'cancel_job', 'list_artifacts', 'read_artifact'} <= names)
                    status = await session.call_tool('environment_status', {})
                    self.assertFalse(getattr(status, 'isError', True), status)
                    pdks = await session.call_tool('list_pdks', {})
                    self.assertFalse(getattr(pdks, 'isError', True), pdks)
                    invalid = await session.call_tool('simulate_netlist', {'netlist': '../escape.spice'})
                    self.assertTrue(getattr(invalid, 'isError', True))
                    job = await session.call_tool('simulate_netlist', {'netlist': filename})
                    self.assertFalse(getattr(job, 'isError', True), job)
                    payload = self.payload(job)
                    job_id = payload['job_id']
                    state = {}
                    for _ in range(100):
                        result = await session.call_tool('job_status', {'job_id': job_id})
                        self.assertFalse(getattr(result, 'isError', True), result)
                        state = self.payload(result)
                        if state['state'] in ('succeeded', 'failed', 'cancelled', 'timed_out'):
                            break
                        await asyncio.sleep(0.1)
                    self.assertEqual(state['state'], 'succeeded', state)
                    logs = await session.call_tool('job_logs', {'job_id': job_id})
                    self.assertFalse(getattr(logs, 'isError', True), logs)
                    self.assertRegex(str(self.payload(logs)), r'5\.0+e-01|0\.5')
                    artifacts = await session.call_tool('list_artifacts', {'job_id': job_id})
                    self.assertFalse(getattr(artifacts, 'isError', True), artifacts)
                    report = await session.call_tool('read_artifact', {'job_id': job_id, 'path': 'output.log'})
                    self.assertFalse(getattr(report, 'isError', True), report)
                    self.assertEqual(self.payload(report)['text'], self.payload(logs)['text'])
                    runners = {
                        'yosys': ('smoke.ys', 'help\n'),
                        'openroad': ('smoke.tcl', 'puts "MCP runner OK"\nexit\n'),
                        'klayout': ('smoke.py', 'print("MCP runner OK")\n'),
                        'magic': ('smoke-magic.tcl', 'puts "MCP runner OK"\nquit -noprompt\n'),
                    }
                    for tool, (script_name, text) in runners.items():
                        script = workspace / script_name
                        self.assertFalse(script.exists(), f'test fixture already exists: {script}')
                        script.write_text(text)
                        try:
                            submitted = await session.call_tool('run_script', {'tool': tool, 'script': script_name})
                            self.assertFalse(getattr(submitted, 'isError', True), submitted)
                            runner_id = self.payload(submitted)['job_id']
                            runner = {}
                            for _ in range(300):
                                runner = self.payload(await session.call_tool('job_status', {'job_id': runner_id}))
                                if runner['state'] not in ('queued', 'running'):
                                    break
                                await asyncio.sleep(0.1)
                            runner_log = self.payload(await session.call_tool('job_logs', {'job_id': runner_id}))
                            self.assertEqual(runner['state'], 'succeeded', (tool, runner, runner_log))
                        finally:
                            script.unlink(missing_ok=True)
                    cancel = await session.call_tool('cancel_job', {'job_id': job_id})
                    self.assertFalse(getattr(cancel, 'isError', True), cancel)
                    print(json.dumps({'tools': sorted(names), 'simulation': state,
                                      'logs': self.payload(logs)}, indent=2))
        finally:
            netlist.unlink(missing_ok=True)

    @staticmethod
    def payload(result):
        if result.structuredContent:
            return result.structuredContent
        return json.loads(result.content[0].text)


if __name__ == '__main__':
    unittest.main()
