# Compatibility boundary with IIC-OSIC-TOOLS

Reference: [IIC-OSIC-TOOLS at 9fc644d1759358280d53cd59addbbd68d72c249a](https://github.com/iic-jku/IIC-OSIC-TOOLS/tree/9fc644d1759358280d53cd59addbbd68d72c249a).
Local baseline: `fbee49843948c4c7ca5ab126ef02d9be1335c580`.

The build architecture, Ubuntu 22.04 base, selected tools, source revisions and
release identity remain local. `manifest.json`, not Dockerfile defaults, supplies
source versions to the build wrappers. The manifest is protected by a host test.
This is interface compatibility, not a clone of upstream's complete tool suite.

| Public interface | Local implementation / intentional boundary |
| --- | --- |
| `start_x.sh` | Local X11 tools from the host terminal; no mandatory XFCE desktop or host networking |
| `start_vnc.sh` | XFCE/noVNC, requires image built with `ENABLE_GUI=1` |
| `start_shell.sh` | Shell-only; host UID/GID by default rather than upstream's root default |
| `start_jupyter.sh` | Jupyter Lab, normal authentication retained |
| `DESIGNS` | Host project directory (default `shared/`) mounted at `/home/designer/shared` |
| `tests/` | Separate test suite mount at `/home/designer/tests`; inputs under `tests/data/`, outputs under `tests/run/` |
| `/foss/designs` | Link to the same project mount, not a second copy |
| `/foss/tools`, `/foss/pdks`, `/headless` | Links to `/opt`, `/opt/pdks`, `/home/designer` |
| `sak-pdk`, `set_pdk` | Two interfaces to one Bash selector, optional installed standard-cell library |
| PDKs | Exactly `ihp-sg13g2`, `sky130A`, `gf180mcuD`; GF A/B/C and additional upstream PDKs are not public |
| `.designinit` | Trusted Bash hook from `$DESIGNS`, loaded once per shell; failures propagate |
| GUI/network | Loopback service ports, no global X permission changes or privilege escalation |
| Runtime portability | Linux amd64 validation; Windows through WSL2, macOS experimental; no claim of Podman/Distrobox/arm64 validation |

GF180MCU D was already built in the baseline. Rehabilitating it means keeping
its shared resources, deterministic patching and verifying analog, technology
and digital workflows. A simulation or smoke flow is not fabrication signoff.
Existing optional Xyce build scripts are retained but Xyce is not newly copied
into the final image. GTKWave continues to come from the existing apt packages.
No osic-multitool or full SAK package is installed.

## Reproducibility limits

Tool/PDK revisions in manifest are unchanged. Some existing Python dependencies,
apt packages, Nix installer and auxiliary Yosys repositories were already
floating; preserving manifest values alone cannot prove their historical binary
identity. Do not manufacture a baseline version or upgrade tools to bypass a
compatibility failure. Build logs and inventories must identify actual results.

## Validation

Host contracts: `python3 -m unittest discover -s tests -p 'test_*.py' -v`.
Docker checks: `CHECK_ONLY=1 ./build/build-image.sh`.
Full image build: `./build/build-image.sh` (standard `ac3e-ic-toolbox` target, including Nix/LibreLane; default image `isaiash/ac3e-ic-toolbox:0.1.0`).
The `ac3e-ic-toolbox-base` target is an intermediate assembly stage, not the standard image.
Optional host integration launcher: `make test`.
In-image suite: `bash /home/designer/tests/run_all.sh` (no `runtime/` dependency).
The release workflow runs host tests and integration tests before authentication
and publication, and uploads failed integration output before cleanup.

See `cleanup-audit.md` for the exact removal scope. Build and integration results
are recorded separately after real execution; this document is not a test-pass claim.

## Maintainer instructions

The active build wrappers read revisions and the release tag from `manifest.json`.
`AGENTS.md` documents the separate `shared/` user workspace and `tests/` mount.
