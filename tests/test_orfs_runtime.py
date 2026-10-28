"""Host-only tests: execute the real ORFS installer against local Git repos."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "images/orfs/install.sh"


class OrfsRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="orfs-runtime-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / "upstream"
        self.source.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "ORFS fixture")
        for path in ("flow/Makefile", "flow/scripts/flow.tcl", "flow/util/metrics.py",
                     "flow/platforms/nangate45/cells.lib", "flow/designs/gcd/config.mk",
                     "tools/AutoTuner/README.md", "LICENSE_BUILD_RUN_SCRIPTS"):
            target = self.source / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fixture resource\n")
        (self.source / ".gitmodules").write_text("".join(
            f'[submodule "tools/{name}"]\n\tpath = tools/{name}\n'
            f'\turl = file:///unavailable-orfs-source/{name}\n'
            for name in ("OpenROAD", "yosys", "yosys-slang")
        ))
        self.git("add", ".")
        self.git("commit", "-qm", "runtime resources")
        self.submodule_sha = self.git("rev-parse", "HEAD").strip()
        for name in ("OpenROAD", "yosys", "yosys-slang"):
            self.git("update-index", "--add", "--cacheinfo",
                     f"160000,{self.submodule_sha},tools/{name}")
        self.git("commit", "-qm", "source gitlinks must not be fetched")
        self.revision = self.git("rev-parse", "HEAD").strip()
        self.tools = self.base / "tools"
        self.tools.mkdir()
        self.target = self.tools / "OpenROAD-flow-scripts"

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args], text=True)

    def install(self):
        env = dict(os.environ, TOOLS=str(self.tools), ORFS_NAME=self.target.name,
                   ORFS_REPO_URL=self.source.as_uri(), ORFS_REPO_COMMIT=self.revision,
                   GIT_ALLOW_PROTOCOL="file", GIT_CONFIG_COUNT="1",
                   GIT_CONFIG_KEY_0="submodule.recurse", GIT_CONFIG_VALUE_0="true")
        return subprocess.run(["bash", str(INSTALLER)], env=env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    def test_provenance_survives_git_removal_at_requested_revision(self):
        # Move upstream HEAD forward: the installer must still use the old pin.
        (self.source / "flow/Makefile").write_text("wrong newer revision\n")
        self.git("commit", "-qam", "newer upstream head")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertFalse((self.target / ".git").exists(), "Git objects leak into final COPY")
        self.assertEqual((self.target / "ORFS_REVISION").read_text(), self.revision + "\n")
        provenance = (self.target / "ORFS_PROVENANCE").read_text()
        self.assertIn(f"repository={self.source.as_uri()}\n", provenance)
        self.assertIn(f"commit={self.revision}\n", provenance)
        for name in ("OpenROAD", "yosys", "yosys-slang"):
            self.assertIn(f"{self.submodule_sha}\ttools/{name}", provenance)
        self.assertEqual((self.target / "flow/Makefile").read_text(), "fixture resource\n")

    def test_make_uses_separately_installed_tools_and_preserves_overrides(self):
        # Upstream flow/Makefile:1-3 includes this customization point before
        # scripts/variables.mk selects tools/install/... defaults (lines 83-112).
        (self.source / "flow/Makefile").write_text(
            '-include settings.mk\n'
            'OPENROAD_EXE ?= missing/tools/install/OpenROAD/bin/openroad\n'
            'OPENSTA_EXE ?= missing/tools/install/OpenROAD/bin/sta\n'
            'YOSYS_EXE ?= missing/tools/install/yosys/bin/yosys\n'
            'all:\n\t@printf "%s\\n" "$(OPENROAD_EXE)" "$(OPENSTA_EXE)" "$(YOSYS_EXE)"\n'
        )
        self.git("commit", "-qam", "flow executable selection")
        self.revision = self.git("rev-parse", "HEAD").strip()
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout)
        binaries = self.base / "separate-tools"
        binaries.mkdir()
        for name in ("openroad", "sta", "yosys"):
            executable = binaries / name
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o755)
        env = dict(os.environ, PATH=f"{binaries}:{os.environ['PATH']}")
        for key in ("OPENROAD_EXE", "OPENSTA_EXE", "YOSYS_EXE"):
            env.pop(key, None)
        output = subprocess.check_output(
            ["make", "--no-print-directory", "-C", str(self.target / "flow")], env=env, text=True
        )
        self.assertEqual(output.splitlines(), [str(binaries / n) for n in ("openroad", "sta", "yosys")])
        output = subprocess.check_output(
            ["make", "--no-print-directory", "-C", str(self.target / "flow"),
             "OPENROAD_EXE=/custom/openroad", "YOSYS_EXE=/custom/yosys"], env=env, text=True
        )
        self.assertEqual(output.splitlines(), ["/custom/openroad", str(binaries / "sta"), "/custom/yosys"])

    def test_runtime_checkout_never_fetches_source_submodules(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stdout)
        for name in ("OpenROAD", "yosys", "yosys-slang"):
            path = self.target / "tools" / name
            self.assertTrue(not path.exists() or not any(path.iterdir()), name)
        for path in ("flow/Makefile", "flow/scripts/flow.tcl", "flow/util/metrics.py",
                     "flow/platforms/nangate45/cells.lib", "flow/designs/gcd/config.mk",
                     "tools/AutoTuner/README.md", "LICENSE_BUILD_RUN_SCRIPTS"):
            self.assertEqual((self.target / path).read_bytes(), (self.source / path).read_bytes())


if __name__ == "__main__":
    unittest.main()
