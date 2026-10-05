from test_pdk_contract import PdkContract, CONFIG
import subprocess

class Entrypoint(PdkContract):
    def run_entry(self, *args):
        return subprocess.run(['bash', str(CONFIG / 'entrypoint.sh'), *args], env=dict(self.env, ENABLE_GUI=''), text=True, capture_output=True)
    def test_argv(self):
        r = self.run_entry('python3', '-c', 'import sys; assert sys.argv[1:] == ["a b", "*", "--flag"]', 'a b', '*', '--flag')
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_entry('printf', '<%s>', 'a b', '*', '--flag')
        self.assertTrue(r.stdout.endswith('<a b><*><--flag>'), r.stdout)
    def test_gui_supervision(self):
        bins = self.base / 'bin'
        bins.mkdir()
        for name in ['vncserver', 'startxfce4', 'vncpasswd']:
            file = bins / name
            file.write_text('#!/bin/bash\n' + ('cat\n' if name == 'vncpasswd' else 'sleep 0.2\n'))
            file.chmod(0o755)
        utils = self.base / 'novnc/utils'
        utils.mkdir(parents=True)
        proxy = utils / 'novnc_proxy'
        proxy.write_text('#!/bin/bash\ntrap "exit 0" TERM\nwhile :; do sleep 0.1; done\n')
        proxy.chmod(0o755)
        env = dict(self.env, ENABLE_GUI='1', VNC_PW='test-secret', NO_VNC_HOME=str(utils.parent), PATH=str(bins) + ':' + self.env['PATH'])
        r = subprocess.run(['bash', str(CONFIG / 'entrypoint.sh'), '--vnc', '--wait'], env=env, text=True, capture_output=True, timeout=5)
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn('test-secret', r.stdout + r.stderr)
        self.assertEqual((self.base / '.vnc/passwd').stat().st_mode & 0o777, 0o600)
        (bins / 'vncserver').write_text('#!/bin/bash\necho $$ > "$HOME/vnc.pid"\ntrap "exit 0" TERM\nwhile :; do sleep 0.1; done\n')
        import time
        import os
        process = subprocess.Popen(['bash', str(CONFIG / 'entrypoint.sh'), '--vnc', '--wait'], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 3
            while not (self.base / 'vnc.pid').exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue((self.base / 'vnc.pid').exists())
            pid = int((self.base / 'vnc.pid').read_text())
            process.terminate()
            process.communicate(timeout=5)
            self.assertEqual(process.returncode, 143)
            with self.assertRaises(ProcessLookupError):
                os.kill(pid, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
    def test_exit_status(self):
        self.assertEqual(self.run_entry('--shell', 'bash', '-c', 'exit 7').returncode, 7)
    def test_invalid_option(self):
        self.assertEqual(self.run_entry('--unknown').returncode, 2)
    def test_headless_vnc(self):
        r = self.run_entry('--vnc', '--wait')
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('ENABLE_GUI=1', r.stderr)
