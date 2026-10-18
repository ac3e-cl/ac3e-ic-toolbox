# SKY Nix adapter (x86_64 Linux)

See the [template workflow and integration tests](../../../docs/librelane-templates.md)
for normal use through `librelane-template`.

This adapter builds LibreLane **3.0.14** from
`f24e0ea5db2260719e9a0c7d51d07db74a87fa23` with Nix and Python 3.11.
`flake.lock` also pins nixpkgs, nix-eda and Ciel. It never installs LibreLane
with pip or modifies the global profile. The parent installer checks out the
manifest-pinned templates and downloads their private PDKs.

`bootstrap.sh ENV_DIR SUPPORT_TOOLS_DIR TEMPLATE_DIR` requires support-tools at
`01d5d2814fa9dd61e9d211e0b235a4a592a9316a`. It installs the unchanged upstream
support-tools/test requirements in a private venv. A `.pth` file appends the Nix
Python closure so that support-tools' exact versions take precedence. Activation
clears inherited Python paths and disables user packages. The venv is not
relocatable: build it at its final path with traversable parent directories.

The KLayout 0.29.12 Python binding is a hash-pinned wheel packaged by Nix with
autoPatchelf, expat, zlib and libstdc++; the CLI remains LibreLane's pinned
KLayout. Ciel is built for Python 3.11 because its upstream overlay captures the
default interpreter. Yosys and OpenROAD retain separate embedded-Python 3.13
packages selected from their own interpreter package sets. The bootstrap runs
`probe-embedded.py` inside both actual tools to catch cross-version injection.

`compat-requirements.txt` adds cryptography 45.0.7 (compatible with upstream's
cffi 1.17.1) and wheel 0.45.1 (required by llN-libparse), without changing the
upstream requirements or Nix locks. The bootstrap requires a clean `pip check`.

Runtime activation (`source ENV_DIR/activate.sh`) does not invoke Nix or require
a writable store. The caller selects the private PDK. The adapter requires
network access, Bash, Git, realpath and configured Nix during installation.

Local contract tests: `python3 images/librelane/sky/test_bootstrap.py`.
