# AC3E IC Toolbox

[![Docker Image Version](https://img.shields.io/docker/v/isaiash/ac3e-ic-toolbox?sort=semver&style=flat-square&logo=docker&label=Release)](https://hub.docker.com/r/isaiash/ac3e-ic-toolbox/tags)
[![License: MIT](https://img.shields.io/badge/License-MIT-lightgrey.svg?style=flat-square)](LICENSE)
[![Issues](https://img.shields.io/github/issues/ac3e-cl/ac3e-ic-toolbox?style=flat-square&label=Issues&logo=github)](https://github.com/ac3e-cl/ac3e-ic-toolbox/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/ac3e-cl/ac3e-ic-toolbox?style=flat-square&label=PRs&logo=github)](https://github.com/ac3e-cl/ac3e-ic-toolbox/pulls)
[![Contributors](https://img.shields.io/github/contributors/ac3e-cl/ac3e-ic-toolbox?style=flat-square&label=Contributors&logo=github)](https://github.com/ac3e-cl/ac3e-ic-toolbox/graphs/contributors)
[![Docker Pulls](https://img.shields.io/docker/pulls/isaiash/ac3e-ic-toolbox?style=flat-square&label=Pulls&logo=docker)](https://hub.docker.com/r/isaiash/ac3e-ic-toolbox)

---

## Quickstart: use the published image (no local build)

From a Linux desktop terminal (or WSL 2 with an X server configured), install
Docker, Git, GNU Make, Bash, `curl`, `jq`, and Python 3. Start Docker and ensure your user
can access it; GUI applications require a working X server and `DISPLAY`.

Download the bootstrap from `main`, optionally inspect it, then run it:

```bash
curl -fsSL https://raw.githubusercontent.com/ac3e-cl/ac3e-ic-toolbox/main/quickstart.sh -o quickstart.sh
bash quickstart.sh
```

The script clones the latest `main` into `./ac3e-ic-toolbox` and runs
`make start`, using the published image version selected by that checkout.
Docker downloads the image only when it is absent locally; the first download
can be large. No toolchain compilation or local image build is needed.
An existing destination is never overwritten. Choose another directory with
`bash quickstart.sh "$HOME/eda-tools"`.

For later sessions, run `cd ac3e-ic-toolbox && make start`.
Designs persist in `shared/`. `make start` resumes the existing stopped container
when its image reference and design directory match; `make attach` also resumes it.
The shell, VNC, and Jupyter launchers likewise reuse their stopped containers.
Reused containers keep their original configuration and command: to apply changed
ports, environment, image contents, or other creation options, remove the stopped
container explicitly before launching again (`make rm` for the default X container).
If the container is already running, the launcher prints a `docker exec` command
to open another shell without stopping or recreating it.
For a terminal without an X server, clone the repository and use `make start-raw`.
The bootstrap URL becomes available when this change is merged into `main`.

The AC3E IC Toolbox repository provides an open-source suite of tools for integrated circuit design, simulation, and verification.

This work is based on:

- [Previous UNIC-CASS IC Design Tools project](https://github.com/unic-cass/uniccass-icdesign-tools)
- [Johannes Kepler University (JKU) IIC-OSIC-TOOLS Docker Image](https://github.com/iic-jku/IIC-OSIC-TOOLS)
- [LibreLane ASIC Implementation Flow](https://github.com/librelane/librelane)
- GoCD NGSpice Agents for CICD VLSI Verification
- Open Source Integrated Circuits Docker Stacks

The standard image includes **[LibreLane](https://github.com/librelane/librelane)**, an ASIC implementation flow based on OpenROAD, Yosys, Magic, and Netgen. LibreLane provides a complete RTL-to-GDSII flow with support for IHP-sg13g2, Sky130, and GF180MCU PDKs, powered by the Nix package manager. Its source revision is pinned in `manifest.json`.

For the IHP, Tiny Tapeout SKY130 and wafer.space GF180 upstream templates, use
the separately pinned Nix environments and private PDKs described in
[LibreLane template workflows and tests](docs/librelane-templates.md).
The global toolbox tools and analog PDKs remain available unchanged.

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
SHARED_DIR=/home/your-user/eda/designs
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
Nix/LibreLane. `ac3e-ic-toolbox-base` is its intermediate EDA assembly stage,
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
DESIGNS="$HOME/eda/designs" PDK=gf180mcuD ./start_shell.sh
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

## MCP integration for AI agents

### Connect with Hermes Agent

Connect to an existing EDA container by its **container name**, not its image
name or release tag. The container must include the bundled MCP server. No
ports, HTTP service, or additional host Python environment are needed.

1. Find your running container with `docker ps --format '{{.Names}}'`.
   If you have not started one, run this from the repository root in a separate
   terminal and leave its shell running:

   ```bash
   CONTAINER_NAME=eda-workbench make start-raw
   ```

   The launcher uses your repository configuration; no image tag is needed in
   the MCP setup.

2. In a host terminal, set the container name and register the server:

   ```bash
   container=eda-workbench  # Replace with your running container's name.
   hermes mcp add ac3e-ic-toolbox --command docker --args exec -i "$container" /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp
   hermes mcp test ac3e-ic-toolbox
   ```

3. Start a new Hermes session and ask:

   > Inspect the EDA environment and list installed PDKs. Do not start a job yet.

Hermes discovers tools with the `mcp_ac3e_ic_toolbox_` prefix. Registration stores
the container name, so the connection does not depend on the image tag. Keep
that name when recreating or upgrading the container. `--args` must be the last
Hermes option; use `-i`, never `-t`, for MCP stdio.

If connection fails, check that Docker is accessible to Hermes, the container
is running, and the server is installed:

```bash
docker exec -i "$container" /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp --help
```

If the command is missing, use an MCP-enabled image or rebuild with `make
build`, then explicitly recreate the container. Updating the checkout alone
does not update an existing container. Compatibility depends on the bundled
server being present, not a particular release number.

### Other MCP clients

Use the same stdio command with any MCP client:

```bash
docker exec -i "$container" /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp
```

Set the client's executable to `docker` and its arguments to `exec`, `-i`,
your container name, and `/opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp`. The client
launches this command; you do not need to run a separate MCP service.
The launcher uses `/opt/ac3e-ic-toolbox/mcp` by default;
`AC3E_IC_TOOLBOX_MCP_HOME` overrides that installation home inside the container.
The default runtime configuration is
`/opt/ac3e-ic-toolbox/config/ac3e-ic-toolbox-env.sh`.
See [Hermes MCP](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp),
[Claude Code MCP](https://code.claude.com/docs/en/mcp), or
[Codex MCP](https://developers.openai.com/codex/mcp/) for client options.

### Workspace, jobs, and agent use cases

The canonical container workspace is `/foss/designs`, backed by the host
`DESIGNS` directory (default: `shared/`). Use container paths in tool calls, not
host paths. Job outputs live beneath `.ac3e-ic-toolbox-mcp/` in that workspace, with
a separate directory identified by each job's UUID; they remain on the host
mount after the MCP connection or container exits.

The server reports tool availability, installed PDK directories, workspace
paths, and job state. Typical agent requests include:

- Inspect available tools and PDKs before choosing a workflow.
- Use `simulate_netlist` to run ngspice on a trusted workspace netlist and
  inspect the resulting logs and files.
- Use `run_script` for trusted Magic Tcl, KLayout Python/Ruby, OpenROAD Tcl,
  or Yosys scripts. Use `tool_catalog` to discover the extended EDA interfaces,
  and `run_tool` for native command-line options (including Netgen).
- Use `start_flow` for a LibreLane design configuration, then poll `job_status`
  and retrieve the job's logs and artifacts through the corresponding tools.

These are execution and inspection primitives, **not a turnkey DRC/LVS
service**. Technology decks, extraction/LVS setup, design inputs, and result
interpretation remain the project's responsibility. Consult the discovered tool
schemas for supported script types, arguments, and limits.

### Extended EDA, filesystem and Linux interfaces

`tool_catalog` documents the native tools, capabilities and argument examples.
`run_tool(tool, arguments, pdk, timeout, cwd)` exposes their native CLI without
shell interpolation, so advanced flags are not restricted to convenience wrappers.
The catalog distinguishes executables from PDK resources and Python libraries;
`environment_status` reports what is actually available in the running image.
GUI applications still need a working display and are session-owned jobs, not
persistent desktop services. The detailed interface is in [MCP tools](docs/mcp-tools.md).

Container filesystem tools are `list_directory`, `stat_path`, `read_file`,
`write_file`, `edit_file`, `make_directory`, `copy_path`, `move_path`,
`remove_path`, and `search_files`. Relative paths use the workspace; absolute
paths access the **entire container**, subject to the server user's permissions.
These tools can also change host files exposed through mounts. Writes do not
overwrite unless explicitly requested; deletion requires `confirm=true` (an API
parameter, **not** an interactive user-approval mechanism). File reads support
UTF-8 or base64 and byte pagination; writes/edits are limited to 1 MiB per call.

`run_command(argv, cwd, pdk, timeout)` executes arbitrary Linux commands without
shell expansion. `run_shell(script, cwd, pdk, timeout)` explicitly enables Bash
pipelines, redirections and shell syntax. Both use the same asynchronous jobs,
timeouts, logs, process-group cancellation and two-job limit as EDA calls.
`list_jobs` lists jobs owned by the connection. Empty `cwd` preserves isolated
job execution; a supplied directory enables in-place project workflows. With a
custom `cwd`, generated files stay there, while `output.log` remains in the
job's `output_dir`; inspect project files with filesystem tools.
Cancellation and shutdown kill the job's original process group. Do not launch
detached daemons (`setsid`, daemonizing services): they can escape that group and
require separate cleanup. An inherited output pipe cannot hold the server open
indefinitely; forced log-drain cutoff is reported as `log_truncated=true`.

Examples of agent requests:

> Show the tool catalog, inspect `rtl/`, then lint my Verilog without changing it.

> Create a netlist in the workspace, simulate it, and read the numerical results.

> Run `df -h` using `run_command`, then inspect the job log.

> Search `project/` for `*.v`, copy the project to a new directory, and operate
> only on the copy. Do not delete or overwrite existing files.

The wrapper accepts `--workspace`, `--config`, and `--pdk-root` options. Paths
refer to files/directories inside the container. Append overrides to the server
command in your client configuration, for example:

```bash
docker exec -i "$container" /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp --workspace /foss/designs
```

Use `--help` and the server configuration/schema for the available policy
settings. The default stdio lifecycle owns jobs within the connection: running
jobs are cancelled on disconnect, but their outputs persist. Job concurrency
is limited to two per connection (not globally across agents). Simulation and
script timeouts default to 300 seconds; LibreLane defaults to 3600 seconds.
Calls can explicitly request a timeout up to 86400 seconds. Submit long work as
jobs and poll it rather than holding a client tool call open for the entire EDA
run. A new MCP connection is not a durable job scheduler.
LibreLane is invoked with `--jobs 2` to bound its internal parallelism.

Example prompts after connecting:

> Inspect the EDA environment and list installed PDKs. Do not start a job yet.

> Simulate `amplifier.spice` with ngspice and `ihp-sg13g2`. Poll the returned
> job ID, read its logs, and report its exit code and operating-point results.

> Run my trusted `checks/layout.py` with KLayout and `gf180mcuD`. List the
> output artifacts and read the text report. Do not treat exit code zero as
> proof that the layout passes DRC unless the report confirms it.

> Start the LibreLane flow from `counter/config.json` using `sky130A` with
> a 7200-second timeout. Poll progress and report errors or final artifacts.

Inputs to the original convenience runners must exist under the workspace;
relative paths are workspace-relative. These runners execute in their output
directories, not the input file's directory. `run_tool`, `run_command` and
`run_shell` can select an explicit container `cwd`. Use
absolute container paths for includes and design sources in scripts/netlists
and LibreLane configurations. LibreLane uses the job directory as its
`--design-dir` and writes beneath `runs/mcp`. `job_status` reports `queued`,
`running`, `succeeded`, `failed`, `timed_out`, or `cancelled`; a successful process
exit does not establish physical-design signoff. `job_logs` and `read_artifact`
return at most 64 KiB per call with byte-offset pagination; combined logs are
capped at 8 MiB. Use `list_artifacts`, `read_artifact`, and `cancel_job` as needed.

### Security boundaries

- Access to the Docker daemon is privileged and can permit host-level control.
  Do not expose it or this integration to untrusted agents/users.
- Netlists, flow configurations, and scripts are executable inputs. They are
  **not sandboxed** merely because they run through MCP or inside Docker;
  scripts can modify mounted designs and access the container's resources.
  Workspace path checks do not sandbox the programs launched by EDA tools.
- Review inputs and configure the client's permissions/approval policy before
  enabling execution tools. MCP itself does not guarantee an agent will ask
  for approval before starting a job.
- Keep secrets out of designs, server configuration, command arguments, and
  logs. Inspection should report selected settings, not dump all environment
  variables; do not ask the agent to collect or expose credentials.

### MCP development tests

The host does not need Python for the bundled runtime connection. Developing
the server does require Python; use an isolated test environment and the pinned
MCP requirements rather than modifying the host's system Python:

```bash
# From the repository root:
python3 -m venv "$HOME/.cache/ac3e-ic-toolbox-mcp-venv"
"$HOME/.cache/ac3e-ic-toolbox-mcp-venv/bin/python" -m pip install -r images/mcp/requirements.txt
# Opt-in live test: eda-workbench must already be running the rebuilt image.
# MCP_TEST_WORKSPACE is the HOST directory mounted as /foss/designs.
export MCP_TEST_COMMAND='["docker","exec","-i","eda-workbench","/opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp"]'
export MCP_TEST_WORKSPACE="$PWD/shared"
"$HOME/.cache/ac3e-ic-toolbox-mcp-venv/bin/python" -m unittest discover -s tests -p 'test_mcp_protocol.py' -v
unset MCP_TEST_COMMAND MCP_TEST_WORKSPACE
# Dependency-free host contracts and the default unittest discovery:
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Protocol tests exercise the MCP SDK connection; host contracts do not validate
the full Docker image or real EDA runs. Validate the rebuilt image and relevant
EDA integration tests separately before treating the integration as released.

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

`tests/run_all.sh` is the only suite runner. It runs directly inside the EDA
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
