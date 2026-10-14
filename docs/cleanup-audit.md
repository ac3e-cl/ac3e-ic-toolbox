# Cleanup audit

Scope: tracked files only, baseline `fbee49843948c4c7ca5ab126ef02d9be1335c580`.
Consumer search covered Dockerfile, Makefile, build scripts, runtime scripts,
CI and documentation using `git grep`; every file below was read before removal.

| Removed path | Evidence / replacement |
| --- | --- |
| `images/final_structure/configure/.bashrc_nix` | No active consumer; shared `ac3e-ic-toolbox-env.sh` replaces alternate Nix configuration |
| `images/final_structure/configure/.bashrc_with_nix` | No active consumer; duplicated tools/PDK setup with different defaults |
| `images/final_structure/configure/install_librelane_nix.sh` | No active consumer; floated dev checkout conflicts with manifest-pinned Dockerfile installation |
| `images/adms/install.sh` | No consumer and no source acquisition; selected target never calls it |
| `images/gocd-agent-ngspice/env.sh` | No consumer/integration present; environment now has a shared supported entry point |
| `images/klayout/install.sh` | Referenced only by a commented Dockerfile stage; active installer remains `images/final_structure/install/install_klayout.sh` |
| `handled_build.sh` | No active consumer; invalid openroad stage, deleted old logs and hid build errors; use build wrappers with pipefail/tee as documented in CONTRIBUTING.md |
| `shared_xserver/verification/gf180mcu/pdk_comparison/gf180mcu_patching.sh` | Exploratory duplicate patch code depending on external unmanaged clones; maintained GF installer/patch/tests replace it |
| `shared_xserver/verification/gf180mcu/pdk_comparison/difference.sh` | Comparison experiment requiring external unmanaged clones; not part of any test or pipeline |
| Obsolete temporary Docker stage | Empty descendant with no consumer; the current manifest targets `ac3e-ic-toolbox`, including Nix/LibreLane, above the intermediate `ac3e-ic-toolbox-base` stage |

Retained: tool dependencies and optional Xyce/GTKWave installers, `draw_efuse.py`,
`fix-tech-file.py`, IHP/Sky patches, notebooks, .mat files, GDS/schematics, original
integration fixtures, other verification examples, images in README, policies,
licenses, issue proposals and devcontainers. Lack of use in CI alone does not make
teaching examples useless.

Protected user entries `IDEA.md` and `shared_xserver/IPD413_202501/` are untouched.
`.env` and credentials are neither read nor edited. `.dockerignore` excludes
these entries and generated/private data from the build context without
excluding build scripts or supported test fixtures. `.hermes` plans are local
and ignored by Git and Docker.

## Separate user workspace and tests

The default user directory is now the initially empty, gitignored `shared/`.
The maintained integration scripts moved from `shared_xserver/tests/` into
the root `tests/`, grouped by tool category. Required fixtures moved from
`artifacts/` to `tests/data/`; generated results live in `tests/run/`.
Runtime launchers and release CI mount the tests at `/home/designer/tests`
separately from user designs.

The unused course checkout, exploratory `verification/` tree and editor files
were removed from the repository workspace after preserving an external local
backup. None was a dependency of the maintained tests; the inverter GDS and
other existing integration inputs are retained under `tests/data/`. `IDEA.md`
and the user's release-version change in `manifest.json` remain untouched.
