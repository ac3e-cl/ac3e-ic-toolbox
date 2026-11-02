# MCP integration for AI agents

### Connect with Hermes Agent

Connect to the `ac3e-ic-toolbox` container, whose name matches `image.name` in
`manifest.json`, not an image reference or release tag. It must include the bundled MCP server. No
ports, HTTP service, or additional host Python environment are needed.

1. If the toolbox is not running, run this from the repository root in a separate
   terminal and leave its shell running:

   ```bash
   make start-raw
   ```

   The launcher uses your repository configuration; no image tag is needed in
   the MCP setup. `make start` also works and reuses `ac3e-ic-toolbox`: a stopped
   container resumes, and the same running version opens another shell. A version
   or image update requires interactive confirmation before replacement (default:
   **No**). Images download only when missing locally or after a confirmed registry
   update. Replacement loses the internal writable layer, but retains designs in
   the host-mounted directory (`shared/` by default).

   A container created with `make start-raw` has no X11 mounts. Remove it
   explicitly with `make rm` before switching to `make start`; a container
   created with `make start` can also serve raw shells. Switching to VNC or
   notebook mode likewise requires explicit recreation.

2. In a host terminal, register the server:

   ```bash
   hermes mcp add ac3e-ic-toolbox --command docker --args exec -i ac3e-ic-toolbox /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp
   hermes mcp test ac3e-ic-toolbox
   ```

3. Start a new Hermes session and ask:

   > Inspect the toolbox and list installed PDKs. Do not start a job yet.

Hermes discovers tools with the `mcp_ac3e_ic_toolbox_` prefix. Registration stores
the container name, so the connection does not depend on the image tag. Keep
that name when recreating or upgrading the container. `--args` must be the last
Hermes option; use `-i`, never `-t`, for MCP stdio.

If connection fails, check that Docker is accessible to Hermes, the container
is running, and the server is installed:

```bash
docker exec -i ac3e-ic-toolbox /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp --help
```

If the command is missing, use an MCP-enabled image or rebuild with `make
build`, then explicitly recreate the container. Updating the checkout alone
does not update an existing container. Compatibility depends on the bundled
server being present, not a particular release number.

### Other MCP clients

Use the same stdio command with any MCP client:

```bash
docker exec -i ac3e-ic-toolbox /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp
```

Set the client's executable to `docker` and its arguments to `exec`, `-i`,
`ac3e-ic-toolbox`, and `/opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp`. The client
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
persistent desktop services. The detailed interface is in [MCP tools](mcp-tools.md).

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
docker exec -i ac3e-ic-toolbox /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp --workspace /foss/designs
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

> Start the LibreLane flow from `counter/config.json` using `gf180mcuD` with
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
# Opt-in live test: ac3e-ic-toolbox must already be running the rebuilt image.
# MCP_TEST_WORKSPACE is the HOST directory mounted as /foss/designs.
export MCP_TEST_COMMAND='["docker","exec","-i","ac3e-ic-toolbox","/opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp"]'
export MCP_TEST_WORKSPACE="$PWD/shared"
"$HOME/.cache/ac3e-ic-toolbox-mcp-venv/bin/python" -m unittest discover -s tests -p 'test_mcp_protocol.py' -v
unset MCP_TEST_COMMAND MCP_TEST_WORKSPACE
# Dependency-free host contracts and the default unittest discovery:
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

Protocol tests exercise the MCP SDK connection; host contracts do not validate
the full Docker image or real EDA runs. Validate the rebuilt image and relevant
EDA integration tests separately before treating the integration as released.
