"""Static contracts for independently schedulable Docker build branches."""
from pathlib import Path
import re
import unittest


DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def stages():
    text = DOCKERFILE.read_text()
    matches = list(re.finditer(r"^FROM\s+(\S+)\s+AS\s+(\S+)\s*$", text, re.M | re.I))
    return {
        match[2]: (match[1], text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)])
        for i, match in enumerate(matches)
    }


class BuildGraphTests(unittest.TestCase):
    def test_light_builder_supplies_magic_glu_headers(self):
        self.assertIn("libglu1-mesa-dev", stages()["builder"][1])

    def test_light_builder_supplies_git_bootstrap_tools(self):
        for package in ("autopoint", "gperf"):
            self.assertIn(package, stages()["builder"][1])

    def test_openvaf_compilation_obeys_job_budget(self):
        installer = (DOCKERFILE.parent / "images/openvaf/install.sh").read_text()
        self.assertIn('cargo build --jobs "${MAX_BUILD_JOBS:-2}"', installer)

    def test_light_builder_does_not_compile_openroad_dependencies(self):
        graph = stages()
        self.assertEqual(graph["builder"][0], "common")
        self.assertNotIn("exhaustive-install.sh", graph["builder"][1])
        for name in ("boost", "swig", "eigen", "cudd", "cusp", "lemon", "spdlog", "gtest", "ortools"):
            self.assertNotIn(f"/images/{name}/install.sh", graph["builder"][1])
        for name in ("magic", "ngspice", "xschem", "netgen", "yosys", "gaw", "cvc_rv", "verilator", "iverilog"):
            self.assertEqual(graph[name][0], "builder")
        deps = graph[graph["openroad_core"][0]][1]
        self.assertIn("/images/ortools/install.sh", deps)
        self.assertIn("COPY --from=openroad_dependencies", graph["ac3e-ic-toolbox-base"][1])

    def test_only_supported_pdk_family_is_built_and_patched(self):
        graph = stages()
        self.assertNotIn('sky130_pdk', graph)
        self.assertNotIn('install_sky130.sh', DOCKERFILE.read_text())
        for name, installer, patch in (
            ("gf180_pdk", "install_gf180mcu.sh", "patch_pdk_gf180mcu.sh"),
        ):
            self.assertIn(name, graph)
            self.assertEqual(graph[name][0], "pdk_builder")
            self.assertIn(installer, graph[name][1])
            self.assertIn(patch, graph[name][1])
        self.assertEqual(graph["pdk_builder"][0], "magic")
        self.assertNotIn("python_packages.sh", graph["pdk_builder"][1])
        self.assertIn("volare==0.18.1", graph["pdk_builder"][1])
        self.assertEqual(graph["open_pdks"][0], "pdk_builder")
        for name in ("gf180_pdk",):
            self.assertRegex(graph["open_pdks"][1], rf"COPY --from={name}\s+\$\{{PDK_ROOT\}}\s+\$\{{PDK_ROOT\}}")


if __name__ == "__main__":
    unittest.main()