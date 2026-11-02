![AC3E IC Toolbox](HEADER.png)

[![Docker Image Version](https://img.shields.io/docker/v/isaiash/ac3e-ic-toolbox?sort=semver&style=flat-square&logo=docker&label=Release)](https://hub.docker.com/r/isaiash/ac3e-ic-toolbox/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg?style=flat-square)](LICENSE)
[![Issues](https://img.shields.io/github/issues/ac3e-cl/ac3e-ic-toolbox?style=flat-square&label=Issues&logo=github)](https://github.com/ac3e-cl/ac3e-ic-toolbox/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/ac3e-cl/ac3e-ic-toolbox?style=flat-square&label=PRs&logo=github)](https://github.com/ac3e-cl/ac3e-ic-toolbox/pulls)
[![Contributors](https://img.shields.io/github/contributors/ac3e-cl/ac3e-ic-toolbox?style=flat-square&label=Contributors&logo=github)](https://github.com/ac3e-cl/ac3e-ic-toolbox/graphs/contributors)
[![Docker Pulls](https://img.shields.io/docker/pulls/isaiash/ac3e-ic-toolbox?style=flat-square&label=Pulls&logo=docker)](https://hub.docker.com/r/isaiash/ac3e-ic-toolbox)
## Quickstart: use the published image (no local build)

From a Linux desktop terminal (or WSL 2 with an X server configured), install
Docker, Git, GNU Make, Bash, `curl`, `jq`, and Python 3. Start Docker and ensure your user
can access it; GUI applications require a working X server and `DISPLAY`.

Run the bootstrap from `main` (inspect the script first if needed):

```bash
curl -fsSL https://raw.githubusercontent.com/ac3e-cl/ac3e-ic-toolbox/main/quickstart.sh | bash
```

The script clones the latest `main` into `./ac3e-ic-toolbox` and runs
`make start`, using the published image version selected by that checkout.
Docker downloads the image only when it is absent locally or you confirm a
registry update; the first download can be large. No local build is needed.
An existing destination is never overwritten. To choose another directory, use
the same pipeline ending with `bash -s -- "$HOME/ac3e-ic-toolbox"`.

For later sessions, run `cd ac3e-ic-toolbox && make start`.
The container is named `ac3e-ic-toolbox`, matching `image.name` in `manifest.json`.
`make start` reuses it: a stopped container resumes, and the same running version
opens another shell. A version or image update requires interactive confirmation
before replacement (default: **No**). Replacement loses the container's internal
writable layer; designs in the host-mounted directory (`shared/` by default) remain.
For a terminal without an X server, clone the repository and use `make start-raw`.
The bootstrap URL becomes available when this change is merged into `main`.

### Connect your AI client through MCP

The bundled MCP server lets a local AI client inspect tools/PDKs, run jobs, and
work with files. Keep `make start` running, or use `make start-raw` without X.
In a host terminal, register **one** client:

| Client | Command |
| --- | --- |
| Claude Code | `claude mcp add --transport stdio ac3e-ic-toolbox -- docker exec -i ac3e-ic-toolbox /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp` |
| Codex | `codex mcp add ac3e-ic-toolbox -- docker exec -i ac3e-ic-toolbox /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp` |
| Cursor | `cursor --add-mcp '{"name":"ac3e-ic-toolbox","command":"docker","args":["exec","-i","ac3e-ic-toolbox","/opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp"]}'` |
| Hermes | `hermes mcp add ac3e-ic-toolbox --command docker --args exec -i ac3e-ic-toolbox /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp` |
| OpenCode | `opencode mcp add` (interactive wizard: choose local, name it `ac3e-ic-toolbox`, paste the command below) |

For OpenCode or **any client supporting local MCP stdio**, use this server command:

```bash
docker exec -i ac3e-ic-toolbox /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp
```

Use `-i`, not `-t`; no HTTP endpoint or published ports are required.
Reload MCP connections or start a new client session.

**Trusted agents only:** execution and filesystem tools can modify mounted host
files; Docker access is privileged. Configure client approvals before use.
See the [connection and troubleshooting guide](docs/mcp-integration.md) and
[tool reference](docs/mcp-tools.md) for details. Client setup references:
[Claude Code](https://code.claude.com/docs/en/mcp),
[Codex](https://developers.openai.com/codex/mcp/),
[Cursor](https://cursor.com/docs/context/mcp),
[Hermes](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp),
[OpenCode](https://opencode.ai/docs/cli/#mcp).

## About

The AC3E IC Toolbox repository provides an open-source suite of tools for integrated circuit design, simulation, and verification.

This work is based on:

- [Previous UNIC-CASS IC Design Tools project](https://github.com/unic-cass/uniccass-icdesign-tools)
- [Johannes Kepler University (JKU) IIC-OSIC-TOOLS Docker Image](https://github.com/iic-jku/IIC-OSIC-TOOLS)
- [LibreLane ASIC Implementation Flow](https://github.com/librelane/librelane)
- GoCD NGSpice Agents for CICD VLSI Verification
- Open Source Integrated Circuits Docker Stacks

The standard image includes **[LibreLane](https://github.com/librelane/librelane)**, an ASIC implementation flow based on OpenROAD, Yosys, Magic, and Netgen. The image supplies IHP-sg13g2 and GF180MCU PDKs, with LibreLane powered by the Nix package manager. Its source revision is pinned in `manifest.json`.

For the IHP and wafer.space GF180 upstream templates, use
the separately pinned Nix environments and private PDKs described in
[LibreLane template workflows and tests](docs/librelane-templates.md).
The global LibreLane installation and IHP/GF analog PDKs remain available.
The `librelane` launcher uses the selected local PDK (`sak-pdk ihp-sg13g2`
or `sak-pdk gf180mcuD`) without Ciel downloads by default. Run
`librelane --smoke-test` to exercise it. Explicit `--ciel-pdk`/`--volare-pdk`
options retain upstream managed-PDK behavior. Python 3.11 remains the user
default; LibreLane and its subprocesses use their isolated Nix Python and tools.
**SKY130 and the Tiny Tapeout SKY template are temporarily excluded** from this
single image to analyze their impact on image size. Their reintroduction is
planned for a later release after this space analysis. SKY tests, fixtures and
test helpers are preserved but skipped through `tests/exclusions.json`, in both
the regular and full suites; they are not counted as passes. There is no alternate
SKY image.

We welcome contributions from the global IC design community!

---

## Supported Operating Systems

- **Linux** (recommended)
- **Windows** (via WSL 2)
- **macOS** (experimental, community support encouraged)

---

## How to Use

No local configuration is required. The manifest defaults to
`isaiash/ac3e-ic-toolbox:0.1.0`. To customize your workstation, optionally create
`.env` with literal `KEY=value` lines, for example:

```bash
# Optional .env contents (replace with your absolute host path):
SHARED_DIR=/home/your-user/ac3e-ic-toolbox/designs
PDK=ihp-sg13g2
```

Edit `.env` to override the Docker image name or tag, PDK, shared directory,
ports, or build behavior. Make targets and launchers read it without evaluating
shell code; exported environment values take precedence. Do not use `export`,
command substitution, `$HOME`, or `~` expansion in `.env`. Direct scripts in
`build/` do not load `.env`: pass environment assignments explicitly, or use
`make build`. An optional `.env.example` documents local settings.

On the first interactive `make start` (also raw, VNC, and notebook starts),
you are asked in English for your development directory. Press Enter to use
the repository's `shared/`. The choice is saved as an absolute `SHARED_DIR`
in the Git-ignored `.env`, preserving other settings; `.env` is created if
missing. An existing directory is used silently. A missing directory is
created and reported as empty. Edit `.env` to change the saved choice.
Explicit `SHARED_DIR` or `DESIGNS` settings skip the prompt and are not
automatically saved. Non-interactive starts use the default without prompting;
dry runs, builds, tests, and configuration inspection never prompt or save it.

Docker, GNU Make, Bash, and `jq` are required for local builds. The committed
[`manifest.json`](manifest.json) is the source of truth for the release version,
image coordinates, final Docker target, and all source URLs and revisions passed
to the Dockerfile. Values in `.env` are optional workstation overrides.

The final `ac3e-ic-toolbox` Docker stage is the standard image and includes
Nix/LibreLane. `ac3e-ic-toolbox-base` is its intermediate tool assembly stage,
not a separate standard runtime variant. Current build commands are:

```bash
make build
./build/build-image.sh
./build/build-stage.sh magic
make STAGE=ihp_pdk build
CHECK_ONLY=1 ./build/build-image.sh
```

Build output defaults to concise stage progress; full diagnostics are saved under
`build/_build_logs/`. On failure, the last 40 log lines and the full log path are
shown. Use `BUILD_VERBOSE=1 make build` for full compiler output, or set
`BUILDKIT_PROGRESS=tty` for native interactive BuildKit output.
See [build performance and diagnostics](docs/build-performance.md) for scheduling,
cache behavior, and resource limits.

### Linux

### Compatible launch commands

All launchers share the same runtime configuration; Make targets remain aliases:

| Launcher | Make alias | Mode |
| --- | --- | --- |
| `./start_x.sh` | `make start` | X11 applications from the host terminal |
| `./start_vnc.sh` | `make start-vnc` | XFCE desktop over VNC/noVNC |
| `./start_shell.sh` | `make start-raw` | Shell only, without GUI sockets |
| `./start_jupyter.sh` | `make start-notebook` | Authenticated Jupyter Lab |

Runtime scripts read optional `.env` settings without evaluating shell code;
explicit environment overrides take precedence. `SHARED_DIR` names the host design
directory (default: the initially empty `shared/`); `DESIGNS` is also supported. Do not set them to different
directories. Shells use the host UID/GID by default (`CONTAINER_USER` and
`CONTAINER_GROUP` override them); `ROOT=1` explicitly requests root.
Launchers provide a private, ephemeral tmpfs HOME owned by that UID/GID and
reuse the installed Nix profile for executable access. Designs persist in the
project mount; HOME settings disappear when the container stops. The image home
permits traversal, not listing or writing, for other users. Direct `docker run
--user` calls must provide equivalent HOME configuration; use the launchers.

```bash
DESIGNS="$HOME/ac3e-ic-toolbox/designs" PDK=gf180mcuD ./start_shell.sh
DRY_RUN=1 ./start_vnc.sh       # Inspect command without Docker/mkdir side effects
ENABLE_GUI=1 BUILD_IMAGE_TAG=ac3e-ic-toolbox:gui ./build/build-image.sh
```

VNC requires an image built with `ENABLE_GUI=1`; changing that variable when
starting a headless image does not install a desktop. Builds never append an
automatic `_vnc` suffix: select your desired image tag explicitly. Service ports
bind to loopback by default: HTTP 8080 (`HTTP_PORT`, legacy `WEBSERVER_PORT`),
VNC 5901 and Jupyter 8888; setting a host port to 0 disables its publication.
Jupyter keeps its standard authentication. Neither passwords nor tokens should
be placed in shared logs. `DOCKER_EXTRA_PARAMS` is whitespace-separated without
shell expansion; quoted strings within it are not interpreted as Bash code.

Inside the container, `/foss/designs` and `/home/designer/shared` refer to the same
mount; `/foss/pdks`, `/foss/tools` and `/headless` link to the existing local paths.
Tests mount separately at `/home/designer/tests`; test fixtures and generated
outputs never belong in the user workspace. `shared/` is gitignored and created
automatically by the launchers when absent.
A project may place a trusted Bash `.designinit` under `$DESIGNS`, for example:

```bash
export PDK=gf180mcuD
export STD_CELL_LIBRARY=gf180mcu_fd_sc_mcu7t5v0
```

This hook executes code once per shell. It is not sandboxed; do not run untrusted
projects. Opening a shell never recompiles IHP OSDI models. Unsupported upstream
PDKs/tools are not installed. See [compatibility boundaries](docs/compatibility-iic-osic.md)
and [cleanup audit](docs/cleanup-audit.md).

### Linux quick start

To open an external terminal when pressing **Play** in Docker Desktop, see
[Docker Desktop terminal setup](docs/docker-desktop-terminal.md), including
Linux, macOS/XQuartz and Windows/WSL configuration. An X11 startup without an
explicit command now opens `xterm`; command-line launchers retain their attached
shell behavior. Existing containers must be recreated to use the updated image.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ac3e-cl/ac3e-ic-toolbox.git
   cd ac3e-ic-toolbox
   ```

2. **Build (optional if using the published image) and run:**
   ```bash
   make build
   make start
   ```

### Windows (with WSL 2)

1. **Install [WSL 2](https://docs.microsoft.com/en-us/windows/wsl/install) and Ubuntu from the Microsoft Store.**

2. **Install required tools:**
   
   **Git Installation:**
   ```powershell
   winget install --id Git.Git -e --source winget
   ```
   
   **Make Installation:**
   ```powershell
   winget install ezwinports.make
   ```

3. **Clone the repository inside your WSL environment:**
   ```bash
   git clone https://github.com/ac3e-cl/ac3e-ic-toolbox.git
   cd ac3e-ic-toolbox
   ```

4. **Run from WSL2:**
   ```bash
   make start
   ```
   **Alternatively, you can use the provided `start.bat` script:**
   - Double-click `start.bat` in Windows Explorer, or
   - Run it from the command prompt:
     ```cmd
     start.bat
     ```

5. **XServer Installation for GUI tools:**
   
   Programs that use graphical user interfaces (xschem, magic, ngspice plots, klayout) require an X Server running on the host machine. Windows requires an external server.
   
   **Install VcXsrv:**
   - Download and install the [21.1.10 release](https://github.com/marchaesen/vcxsrv/releases/download/21.1.10/vcxsrv-64.21.1.10.0.installer.exe) from the [VcXsrv releases page](https://github.com/marchaesen/vcxsrv/releases/tag/21.1.10)
   - **Important:** Add the installation directory to your system `Path`:
     1. Open Control Panel and search for environment variables
     2. Select the option that modifies current account
     3. In **User Variables**, add the VcXsrv directory to the `Path` user variable
     4. Reopen each terminal to reload the path
   
   **Note:** We recommend version 21.1.10 as newer versions may have security concerns.

6. **Note:** Some tools may require additional configuration or may not be fully supported.

### macOS (experimental)

1. **Install [XQuartz](https://www.xquartz.org/) for GUI tools:**
   
   Programs that use graphical user interfaces (xschem, magic, ngspice plots, klayout) require an X Server running on the host machine. macOS requires an external server.

2. **Clone the repository:**
   ```bash
   git clone https://github.com/ac3e-cl/ac3e-ic-toolbox.git
   cd ac3e-ic-toolbox
   ```

3. **Run the Docker environment:**
   ```bash
   make start
   ```

4. **Note:** macOS support is experimental. Community support and contributions are encouraged.

---

## Installed Tools / PDKs

| Tool         | Description                                         | Source |
|--------------|-----------------------------------------------------|--------|
| **librelane** | Complete RTL-to-GDSII ASIC implementation flow     | Nix    |
| openroad     | Physical design platform; standalone and LibreLane environments | System / Nix |
| ngspice      | SPICE analog and mixed-signal simulator             | System |
| gnucap       | GNU Circuit Analysis Package (20260729-dev)         | System |
| xschem       | Schematic Editor                                    | System |
| magic        | Layout editor with DRC/Extraction capabilities      | System |
| klayout      | Layout viewer and editor for GDS                    | System; LibreLane uses its Nix environment |
| netgen       | Netlist Comparison                                  | System |
| yosys        | RTL synthesis framework                             | System |
| verilator    | Verilog simulator                                   | System |
| iverilog     | Icarus Verilog simulator                            | System |
| cvc          | Circuit validity checker                            | System |
| cace         | Circuit Characterization engine                     | System |
| gdsfactory   | Python module for GDS generation                    | System |
| glayout      | Python module for PDK-agnostic layout automation    | System |
| pygmid       | Python module for systematic circuit sizing         | System |
| openvaf      | Verilog-A to OSDI compiler                          | System |

### Python environments

EDA Python packages use CPython 3.11.18 installed side-by-side with Ubuntu's
system Python, with `/opt/eda-venv/bin` selected by default on `PATH`.
`/usr/bin/python3` remains Ubuntu 22.04's Python 3.10; it is not replaced.
The global and template-specific Nix environments keep their own interpreters
and dependencies rather than sharing the EDA venv.

The pinned Ubuntu KLayout `.deb` embeds Python **3.10**, regardless of `PATH`.
Its GF180 PCells have a separate `/opt/klayout-pcells` venv containing `numpy<2`,
`gdsfactory<8` (the PCells use the pre-8 `typings`/`geometry` API), and their
required transitive dependencies—not the full user EDA package list.
`/usr/local/bin/klayout` wraps `/usr/bin/klayout` and sets `KLAYOUT_PYTHONPATH`
only for that process, retaining explicit caller KLayout paths. It also disables
user-site imports for that process. No global `PYTHONPATH` or Python 3.11
site-packages changes are needed. Calling `/usr/bin/klayout` directly bypasses
this dependency setup. KLayout's [0.30.11 interpreter initialization](https://github.com/KLayout/klayout/blob/v0.30.11/src/pya/pya/pya.cc#L208-L231)
explicitly maps `KLAYOUT_PYTHONPATH` into its embedded interpreter; its bundled
`pymod` directory is prepended before these dependency paths. Inspection of the
pinned Ubuntu-22 `.deb` confirms both the environment-variable string and the
`libpython3.10.so.1.0` ELF dependency. The [pinned GF generators](https://github.com/efabless/globalfoundries-pdk-libs-gf180mcu_fd_pr/tree/a11222d681f2134ab28e97f97b9b99b6af188f88/cells/klayout/pymacros/cells)
are the source of the compatibility dependencies.

Image build and runtime validation are still required. The real-image gate is
`bash /home/designer/tests/pdk/klayout-gf180-tech.sh`: it checks embedded Python
3.10, imports from the isolated venv, and generates/reopens a GF180 nfet GDS.
The additional dependency closure/image size has not been measured.

### LibreLane Integration

[LibreLane](https://github.com/librelane/librelane) is available directly from the command line and provides:
- Complete RTL-to-GDSII automated flow
- Installed PDK support (IHP-sg13g2, GF180MCU D)
- Design exploration and optimization
- Integration with industry-standard IC design tools

**Quick start with LibreLane:**
```bash
librelane --help           # Show available options
# Run a small complete flow with the retained GF180 PDK:
bash /home/designer/tests/pdk/librelane-gf180-smoke.sh
# For your own config, select its installed PDK explicitly:
librelane --manual-pdk --pdk-root /opt/pdks --pdk gf180mcuD path/to/config.json
```

### PDK Management

The image contains the `gf180mcuD` and `ihp-sg13g2` PDKs. GF180MCU D is a supported PDK, not a deprecated optional download. To change between PDKs, use `sak-pdk` (compatible with IIC-OSIC-TOOLS) or the equivalent legacy `set_pdk` function:

```bash
sak-pdk             # List installed supported PDKs
sak-pdk ihp-sg13g2   # Default PDK

sak-pdk gf180mcuD gf180mcu_fd_sc_mcu7t5v0
set_pdk gf180mcuD    # Equivalent legacy interface
```

Selection updates `PDK`, `PDKPATH`, `STD_CELL_LIBRARY`,
`SPICE_USERINIT_DIR` and `KLAYOUT_PATH`; GF D sets `GF_PDK_OPTION=D`.
Unsupported PDKs (including GF C) fail without changing the previous selection.
An optional second argument must name an installed standard-cell library.

GNUCAP is built from the official Codeberg repository using its `INSTALL`
instructions, with the `20260729-dev` snapshot pinned by SHA in `manifest.json`.
Build it independently with `./build/build-stage.sh gnucap`. Inside the image,
run `bash /home/designer/shared/tests/gnucap.sh` to verify a 10 V resistor divider
produces 5 V. This standalone test lives in the shared workspace as requested;
it is not discovered by `tests/run_all.sh`. No additional GNUCAP extensions or
PDK model compatibility are implied by this smoke test.

The IHP PDK Verilog-A models are compiled into OSDI binaries during the image build (`ihp_pdk` stage). The canonical location is `libs.tech/ngspice/osdi/`; a compatibility symlink at `libs.tech/ngspice/openvaf/` points to the same files for older schematics that reference the legacy path.

Versions, commit references, and source URLs for all tools and PDKs are specified
in [`manifest.json`](manifest.json). Build through `make build`,
`build/build-image.sh`, or `build/build-stage.sh`; these wrappers validate the
manifest and pass its values to the otherwise static Dockerfile.

---

## Testing

`tests/run_all.sh` is the only suite runner. It runs directly inside the toolbox
container without requiring the repository's `runtime/` directory or Docker
commands. The tests mount separately from the user workspace:

```bash
# Inside a container with tests/ mounted:
bash /home/designer/tests/run_all.sh
# Optional host convenience command (starts a temporary container):
make test
# An explicit local image, without changing manifest.json:
DOCKER_USER= DOCKER_IMAGE=ac3e-ic-toolbox DOCKER_TAG=gui make test
```

Tests are organized under `tests/analog/`, `digital/`, `gui/`, `inventory/` and
`pdk/`. Only required inputs are stored in `tests/data/`. The runner discovers
every shell test in these folders, continues after failures, and prints a final
per-test summary. It exits 0 when every non-excluded test passes; missing tools
are failures unless explicitly excluded in `tests/exclusions.json`. Xyce, MCY
inventory checks and ORFS are excluded by user decision and remain visible in
the summary, never counted as passes. `TEST_TIMEOUT` controls the per-test limit (900 seconds by
default). Generated files, individual logs and `summary.tsv` are written under
the gitignored `tests/run/`.

The suite checks the two retained IHP/GF PDK environments, a GF180MCU MOSFET operating
point, GF KLayout technology/PCells and an explicit GF LibreLane counter flow
with final metrics and GDS checks.

The no-SKY image requires a rebuild and container integration runs; historical
image results are not validation of this change. Full IHP/GF template flows
remain explicit opt-in tests (`bash /home/designer/tests/test_all_full.sh`).
Host runtime contracts run without design tools:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
CHECK_ONLY=1 ./build/build-image.sh
```

---

## Publishing a Release

The release workflow builds and publishes an image whenever a branch named
`release/x.y.z` is pushed. The branch version must exactly match
`release.version` in `manifest.json`.

Before using the workflow, configure these settings in the new GitHub repository:

- `DOCKERHUB_USERNAME`: the Docker Hub account used to publish the image.
- `DOCKERHUB_TOKEN`: a least-privilege Docker Hub access token with push access
  to the repository declared under `image` in `manifest.json` (`isaiash/ac3e-ic-toolbox`).

The workflow targets GitHub's `release-env` Actions environment. Create that
environment under Settings → Environments, or change `environment: release-env`
in `.github/workflows/docker-release.yml` to an existing environment. If the
secrets are environment-scoped, add both there; otherwise repository-level
Actions secrets work. Ensure Actions are enabled and the workflow has permission
to read repository contents. The workflow builds from `release/x.y.z` branches;
the version must match `release.version` in `manifest.json`. GitHub Actions does
not need a repository URL variable—the checkout is the triggering repository.

No GitHub Actions repository variables are required. In Docker Hub, set the
repository tag mutability policy to **All tags are mutable**. A repeated
successful build of the same `release/x.y.z` branch then updates the existing
`x.y.z` tag when `docker push` runs.

To publish a release:

1. Update `release.version` and any tool or PDK revisions in `manifest.json`.
2. Commit the release configuration.
3. Create and push the matching branch, for example:

   ```bash
   git switch -c release/0.1.0
   git push origin release/0.1.0
   ```

The workflow validates the manifest and Dockerfile, builds the image through
`build/build-image.sh`, runs `tests/run_all.sh` inside that exact
image, and logs in and pushes to Docker Hub only after every test passes. It can
also be rerun manually from the matching release branch.

The job timeout is six hours. It currently uses the standard `ubuntu-latest`
runner and reclaims preinstalled software before building. This runner only
guarantees 14 GB of SSD space, while the current published image is about
5.55 GB compressed, so disk exhaustion remains a significant risk. If that
occurs, move the job to a GitHub larger runner or a self-hosted Linux x64 runner
with at least 150 GB of free disk.

---

## Additional Details

- **LibreLane Documentation:**  
  Visit the [official LibreLane documentation](https://librelane.readthedocs.io) for detailed guides on running ASIC flows, configuring designs, and using advanced features.
  
- **Nix Package Manager:**  
  The image uses [Nix](https://nixos.org) for reproducible package management. You can install additional tools using `nix profile install nixpkgs#<package>` or create temporary environments with `nix-shell -p <package>`.

- **Tool Documentation:**  
  Each tool directory contains specific documentation and usage instructions. For LibreLane-specific workflows, refer to the [LibreLane GitHub repository](https://github.com/librelane/librelane).

- **Community & Support:**  
  - For general issues: [GitHub Issues](https://github.com/ac3e-cl/ac3e-ic-toolbox/issues)
  - For LibreLane-specific questions: [FOSSi Chat Matrix Server](https://matrix.to/#/#openlane:fossi-foundation.org)

- **License:**  
  This project is licensed under the [MIT License](LICENSE). LibreLane is licensed under [Apache License 2.0](https://github.com/librelane/librelane/blob/main/License).
