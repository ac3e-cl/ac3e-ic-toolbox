# UNIC-CASS IC Design Tools

[![Docker Image Version](https://img.shields.io/docker/v/isaiassh/unic-cass-tools?sort=semver&style=flat-square&logo=docker&label=Release)](https://hub.docker.com/r/isaiassh/unic-cass-tools/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg?style=flat-square)](LICENSE)
[![Issues](https://img.shields.io/github/issues/unic-cass/uniccass-icdesign-tools?style=flat-square&label=Issues&logo=github)](https://github.com/unic-cass/uniccass-icdesign-tools/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/unic-cass/uniccass-icdesign-tools?style=flat-square&label=PRs&logo=github)](https://github.com/unic-cass/uniccass-icdesign-tools/pulls)
[![Contributors](https://img.shields.io/github/contributors/unic-cass/uniccass-icdesign-tools?style=flat-square&label=Contributors&logo=github)](https://github.com/unic-cass/uniccass-icdesign-tools/graphs/contributors)
[![Docker Pulls](https://img.shields.io/docker/pulls/isaiassh/unic-cass-tools?style=flat-square&label=Pulls&logo=docker)](https://hub.docker.com/r/isaiassh/unic-cass-tools)

---

The UNIC-CASS IC Design Tools repository provides a comprehensive, open-source suite of tools for Integrated Circuit (IC) design, simulation, and verification. This project is part of the Universalization of IC Design from CASS (UNIC-CASS) program—a structured, end-to-end IC design-to-test experiential learning initiative.

This work is based on:

- [Johannes Kepler University (JKU) IIC-OSIC-TOOLS Docker Image](https://github.com/iic-jku/IIC-OSIC-TOOLS)
- [LibreLane ASIC Implementation Flow](https://github.com/librelane/librelane)
- GoCD NGSpice Agents for CICD VLSI Verification
- Open Source Integrated Circuits Docker Stacks

**New in v1.0.3**: This image now integrates **[LibreLane](https://github.com/librelane/librelane)** (v3.0.0.dev40), a modern ASIC implementation flow based on OpenROAD, Yosys, Magic, and Netgen. LibreLane provides a complete RTL-to-GDSII flow with support for IHP-sg13g2, Sky130, and GF180MCU PDKs, powered by the Nix package manager for reproducible builds.

We welcome contributions from the global IC design community!

---

## Supported Operating Systems

- **Linux** (recommended)
- **Windows** (via WSL 2)
- **macOS** (experimental, community support encouraged)

---

## How to Use

Create your local environment configuration from the committed example before building or running the image:

```bash
cp .env.example .env
```

Edit `.env` to override the Docker image name or tag, PDK, shared directory,
ports, or build behavior. Make targets load it automatically. When invoking a
script in `build/` directly, first run
`set -a; source .env; set +a`.

Docker, GNU Make, Bash, and `jq` are required for local builds. The committed
[`manifest.json`](manifest.json) is the source of truth for the release version,
image coordinates, final Docker target, and all source URLs and revisions passed
to the Dockerfile. Values in `.env` are optional workstation overrides.

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
explicit environment overrides take precedence. `DESIGNS` names the host design
directory (default: the initially empty `shared/`); `SHARED_DIR` remains a legacy alias. Do not set them to different
directories. Shells use the host UID/GID by default (`CONTAINER_USER` and
`CONTAINER_GROUP` override them); `ROOT=1` explicitly requests root.
Launchers provide a private, ephemeral tmpfs HOME owned by that UID/GID and
reuse the installed Nix profile for executable access. Designs persist in the
project mount; HOME settings disappear when the container stops. The image home
permits traversal, not listing or writing, for other users. Direct `docker run
--user` calls must provide equivalent HOME configuration; use the launchers.

```bash
DESIGNS="$HOME/eda/designs" PDK=gf180mcuD ./start_shell.sh
DRY_RUN=1 ./start_vnc.sh       # Inspect command without Docker/mkdir side effects
ENABLE_GUI=1 BUILD_IMAGE_TAG=unic-cass-compat:gui ./build/build-image.sh
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

1. **Clone the repository:**
   ```bash
   git clone https://github.com/unic-cass/uniccass-icdesign-tools.git
   cd uniccass-icdesign-tools
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
   git clone https://github.com/unic-cass/uniccass-icdesign-tools.git
   cd uniccass-icdesign-tools
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
   git clone https://github.com/unic-cass/uniccass-icdesign-tools.git
   cd uniccass-icdesign-tools
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

### LibreLane Integration

[LibreLane](https://github.com/librelane/librelane) is available directly from the command line and provides:
- Complete RTL-to-GDSII automated flow
- Multi-PDK support (IHP-sg13g2, Sky130A, GF180MCU)
- Design exploration and optimization
- Integration with industry-standard EDA tools

**Quick start with LibreLane:**
```bash
librelane --help           # Show available options
librelane --smoke-test     # Run a quick verification test
librelane <config.json>    # Run a design flow
```

### PDK Management

The image contains the `sky130A`, `gf180mcuD`, and `ihp-sg13g2` PDKs. GF180MCU D is a supported PDK, not a deprecated optional download. To change between PDKs, use `sak-pdk` (compatible with IIC-OSIC-TOOLS) or the equivalent legacy `set_pdk` function:

```bash
sak-pdk             # List installed supported PDKs
sak-pdk ihp-sg13g2   # Default PDK
sak-pdk sky130A
sak-pdk gf180mcuD gf180mcu_fd_sc_mcu7t5v0
set_pdk gf180mcuD    # Equivalent legacy interface
```

Selection updates `PDK`, `PDKPATH`, `STD_CELL_LIBRARY`,
`SPICE_USERINIT_DIR` and `KLAYOUT_PATH`; GF D sets `GF_PDK_OPTION=D`.
Unsupported PDKs (including GF C) fail without changing the previous selection.
An optional second argument must name an installed standard-cell library.

The IHP PDK Verilog-A models are compiled into OSDI binaries during the image build (`ihp_pdk` stage). The canonical location is `libs.tech/ngspice/osdi/`; a compatibility symlink at `libs.tech/ngspice/openvaf/` points to the same files for older schematics that reference the legacy path.

Versions, commit references, and source URLs for all tools and PDKs are specified
in [`manifest.json`](manifest.json). Build through `make build`,
`build/build-image.sh`, or `build/build-stage.sh`; these wrappers validate the
manifest and pass its values to the otherwise static Dockerfile.

---

## Testing

`tests/run_all.sh` is the only suite runner. It runs directly inside the EDA
container without requiring the repository's `runtime/` directory or Docker
commands. The tests mount separately from the user workspace:

```bash
# Inside a container with tests/ mounted:
bash /home/designer/tests/run_all.sh
# Optional host convenience command (starts a temporary container):
make test
# An explicit local image, without changing manifest.json:
DOCKER_USER= DOCKER_IMAGE=unic-cass-compat DOCKER_TAG=gui make test
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

The suite also verifies the three PDK environments, a GF180MCU MOSFET operating
point, GF KLayout technology/PCells and an explicit GF LibreLane counter flow
with final metrics and GDS checks. Host runtime contracts run without EDA tools:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
CHECK_ONLY=1 ./build/build-image.sh
```

---

## Publishing a Release

The release workflow builds and publishes an image whenever a branch named
`release/x.y.z` is pushed. The branch version must exactly match
`release.version` in `manifest.json`.

Before using the workflow, configure these repository Actions secrets:

- `DOCKERHUB_USERNAME`: the Docker Hub account used to publish the image.
- `DOCKERHUB_TOKEN`: a least-privilege Docker Hub access token with push access
  to the repository declared under `image` in `manifest.json`.

No GitHub Actions repository variables are required. In Docker Hub, set the
repository tag mutability policy to **All tags are mutable**. A repeated
successful build of the same `release/x.y.z` branch then updates the existing
`x.y.z` tag when `docker push` runs.

To publish a release:

1. Update `release.version` and any tool or PDK revisions in `manifest.json`.
2. Commit the release configuration.
3. Create and push the matching branch, for example:

   ```bash
   git switch -c release/1.3.0
   git push origin release/1.3.0
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
  - For general issues: [GitHub Issues](https://github.com/unic-cass/uniccass-icdesign-tools/issues)
  - For LibreLane-specific questions: [FOSSi Chat Matrix Server](https://matrix.to/#/#openlane:fossi-foundation.org)

- **License:**  
  This project is licensed under the [MIT License](LICENSE). LibreLane is licensed under [Apache License 2.0](https://github.com/librelane/librelane/blob/main/License).
