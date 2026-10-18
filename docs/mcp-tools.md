# MCP tool reference

The bundled stdio server runs **inside the container**. Connect using
`docker exec -i <container> /opt/ac3e-ic-toolbox/mcp/bin/ac3e-ic-toolbox-mcp`.
Rebuild/recreate the runtime to install source changes, then reconnect your MCP
client to refresh discovery. No TCP listener or new Python dependencies are added.

## EDA interfaces

| Interface | Capabilities |
| --- | --- |
| `tool_catalog` | Native CLI descriptions, example argv, capabilities, resource and exclusion notes. Not an availability probe. |
| `environment_status`, `list_pdks` | Availability of catalog executables, workspace/config paths and installed PDK directories. No environment-variable dump. |
| `run_tool` | Native options for every catalog executable; literal argument array, optional PDK, cwd and timeout. |
| `simulate_netlist` | Existing ngspice/Xyce batch simulation. |
| `run_script` | Existing Yosys, OpenROAD, KLayout and Magic script execution. |
| `run_tool_script` | Netgen Tcl, Xschem Tcl, GNUCAP batch commands and OpenSTA Tcl. |
| `xschem_netlist` | Headless schematic netlisting with optional explicit rcfile. |
| `netgen_lvs` | Reference/implementation netlists and top cells, optional setup Tcl, `lvs.log`. Inspect report for equivalence. |
| `lint_verilog` | Verilator lint, explicit sources/top and additional native arguments. |
| `compile_verilog` | Icarus compilation, standard/top/output selection, additional arguments. |
| `run_vvp` | Execute a compiled Icarus artifact, including output from a prior job. |
| `compile_veriloga` | OpenVAF compilation to an OSDI model. |
| `run_formal` | EQY/SBY configs, or MCY project cwd/subcommands. Inspect proof/coverage artifacts. |
| `start_flow` | Existing LibreLane manual-PDK flow with two internal workers. |

Native catalog executables: `gnucap`, `ngspice`, `Xyce`, `magic`, `openvaf`,
`klayout`, `xschem`, `netgen`, `gaw`, `yosys`, `eqy`, `sby`, `mcy`, `cvc_rv`,
`verilator`, `iverilog`, `vvp`, `gtkwave`, `openroad`, `librelane`, `nix`, `sta`.
CVC is the **Circuit Validity Checker**, not a Verilog simulator.

Xyce and MCY are excluded by the current repository runtime policy; their
interfaces work only if the executable is installed. Standalone `sta` is optional.
GNUCAP availability requires an image including its installer. Formal engines,
GUI displays and technology decks are not supplied by the MCP server. GAW,
GTKWave and GUI modes require an existing working display. PDKs and ORFS are
resources, not executable names accepted by `run_tool`; use `run_command`/`run_shell`
for make-based ORFS workflows. Native tool availability does not prove
cross-tool compatibility or successful physical-design signoff.

Convenience-runner source/config paths must exist inside the workspace, outside
job-output directories. `run_vvp` deliberately also accepts generated artifacts.
Native `run_tool` arguments are passed unchanged: use **absolute container input
paths** unless setting a project `cwd`. Extra native flags can override the
convenience defaults and are trusted. Output filenames of compilation wrappers
must be single filenames. With default cwd they are job artifacts; with custom
cwd they are project files. `run_formal` EQY/SBY output directory is `formal/`;
use separate cwd directories to avoid collisions across runs.

## Files and directories

| Interface | Behavior |
| --- | --- |
| `list_directory` | Sorted entries including hidden files, paginated metadata. |
| `stat_path` | Type, byte size, permissions, UID/GID, modification time, symlink target. |
| `read_file` | UTF-8 or base64, byte offsets, up to 64 KiB per page. |
| `write_file` | Create UTF-8/base64 file; `overwrite=true` required to replace existing content. Parents must exist. |
| `edit_file` | Exact UTF-8 replacement; unique match by default, `replace_all=true` for repeated matches. Preserves line endings. |
| `make_directory` | Create directory; `parents=true` creates ancestors and permits existing directories. |
| `copy_path` | Copy files/trees while preserving symlinks; destination must not exist. |
| `move_path` | Move file/tree; destination must not exist. |
| `remove_path` | Requires `confirm=true`; nonempty directories also need `recursive=true`. Protects workspace and its ancestors. |
| `search_files` | Recursive basename glob; no symlink descent, paginated, 100000-entry scan cap. |

Relative paths use `workspace`. Absolute paths and symlink targets may access the
entire container, including mounted host directories, subject to Unix permissions.
These are trusted-local operations, not a race-proof filesystem sandbox; avoid
concurrent modifications to the same paths. File IO rejects special files such
as devices and FIFOs. Writes and resulting edits are capped at 1 MiB; base64
input also has a 1 MiB character cap. List/search page limits are 1000 entries.
`search_files.scan_truncated=true` means the scan cap prevented complete results;
permission-denied subtrees can also be omitted by the native directory walker.
Use Linux commands for archives, content search, permissions, checksums and other
operations, with explicit client authorization for destructive work.

## Linux and jobs

- `run_command(argv, cwd='', pdk='', timeout=300)`: arbitrary command argv,
  no implicit shell expansion, standard input closed.
- `run_shell(script, cwd='', pdk='', timeout=300)`: explicit Bash syntax,
  pipelines and redirections, with `pipefail` enabled.
- `list_jobs`, `job_status`, `job_logs`, `cancel_job`, `list_artifacts`,
  `read_artifact`: session-owned asynchronous execution and output inspection.

Execution first sources the configured EDA environment and then reapplies an
explicit PDK. No environment secrets are included in job metadata. Empty cwd
creates isolated output directories under `.ac3e-ic-toolbox-mcp/<uuid>`; a supplied
cwd runs in place but logs remain in that job's output directory. `job_status`
reports both paths. Project files outside output_dir are accessed with filesystem
calls rather than `list_artifacts`.

There are two concurrent jobs per connection. Timeouts are positive and at most
86400 seconds. Logs are capped at 8 MiB and read in 64 KiB byte pages. Session
shutdown cancels original process groups; output files persist, job state does
not. Commands must not daemonize: processes detaching into new sessions can
escape cancellation and need separate cleanup. Retained descendant stdout has a
bounded drain grace; forced cutoff sets `log_truncated=true`. No durable scheduler,
interactive terminal or automatic user-approval UI is provided.

**Security:** filesystem and Linux tools can modify the container and mounted
host files. An executable allowlist and workspace checks on selected wrappers do
not restrict trusted scripts. Configure MCP-client permissions before connecting;
`confirm=true` is only an API parameter, not evidence of human approval.

## Verification scope

Host unittests include executable fixtures testing argument construction and
process behavior, not real EDA functionality. The opt-in `test_mcp_protocol.py`
uses the installed launcher and SDK to check discovery, filesystem operations,
Linux commands, native Yosys, Verilator lint, Icarus compilation/VVP, numerical
ngspice output, the original script runners and artifact reads. See the README
for invocation. A focused overlay on an existing image verifies MCP changes but
is not a complete source-image rebuild or validation of every EDA flow.
