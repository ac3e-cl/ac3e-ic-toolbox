import os
from pathlib import Path
import pty

import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SharedSetup(unittest.TestCase):
    def test_first_start_persists_and_creates_directory(self):
        self.check_setup()

    def test_existing_directory_is_used_silently_and_settings_preserved(self):
        self.check_setup(existing=True)

    def test_enter_saves_default(self):
        self.check_setup(default=True)

    def test_noninteractive_start_creates_env_without_prompt(self):
        self.check_setup(interactive=False)

    def check_setup(self, existing=False, default=False, interactive=True):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = Path(tmp)
            (root / 'runtime').mkdir()
            shutil.copy(ROOT / 'runtime/start.sh', root / 'runtime/start.sh')
            shutil.copy(ROOT / 'manifest.json', root / 'manifest.json')
            docker = root / 'docker'
            docker.write_text('#!/bin/bash\nexit 0\n')
            docker.chmod(0o755)
            config = root / '.env'
            designs = root / ('shared' if default or not interactive else 'new designs')
            if existing:
                designs.mkdir()
                config.write_text('# Keep this setting\nSHARED_DIR=\nPDK=ihp-sg13g2')
            env = {k: v for k, v in os.environ.items()
                   if k not in ('DESIGNS', 'SHARED_DIR', 'ENV_FILE', 'DRY_RUN')}
            env.update(PATH=str(root) + ':' + os.environ['PATH'], NO_PULL='1')

            def launch(answer=None):
                master, slave = pty.openpty()
                process = subprocess.Popen(['bash', str(root / 'runtime/start.sh'), 'shell'],
                                           stdin=slave if interactive else subprocess.DEVNULL, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, env=env)
                os.close(slave)
                if answer is not None:
                    os.write(master, (answer + '\n').encode())
                try:
                    out, err = process.communicate(timeout=10)
                finally:
                    os.close(master)
                self.assertEqual(process.returncode, 0, err.decode())
                return err.decode()

            output = launch('' if default else str(designs))
            self.assertTrue(designs.is_dir())
            if not interactive:
                self.assertNotIn('Development directory', output)
                self.assertEqual(config.read_text(), '')
                return
            self.assertIn('Development directory', output)
            if existing:
                self.assertNotIn('created an empty directory', output)
                self.assertIn('# Keep this setting\nPDK=ihp-sg13g2\n', config.read_text())
            else:
                self.assertIn('created an empty directory', output)
            self.assertIn(f'SHARED_DIR={designs}', config.read_text())
            saved = config.read_text()
            self.assertNotIn('Development directory', launch())
            self.assertEqual(config.read_text(), saved)


if __name__ == '__main__':
    unittest.main()
