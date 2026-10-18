"""Adapter contract; integration is exercised in the disposable container."""
import pathlib
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent


class BootstrapContract(unittest.TestCase):
    def test_missing_arguments_do_not_create_an_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(["bash", str(HERE / "bootstrap.sh")], cwd=directory,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Usage:", result.stderr)
            self.assertEqual(list(pathlib.Path(directory).iterdir()), [])


    def test_unpinned_support_tools_are_rejected_before_nix(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", "-q", directory], check=True)
            subprocess.run(["git", "-C", directory, "-c", "user.name=Test", "-c",
                            "user.email=test@example.invalid", "commit", "-q", "--allow-empty", "-m", "test"], check=True)
            result = subprocess.run(["bash", str(HERE / "bootstrap.sh"), directory + "/env", directory, directory],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("Wrong support-tools revision", result.stderr)
            self.assertFalse(pathlib.Path(directory, "env").exists())


if __name__ == "__main__":
    unittest.main()
