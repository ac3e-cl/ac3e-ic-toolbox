# ORFS runtime distribution

`install.sh` checks out the manifest revision without initializing source
submodules. OpenROAD and Yosys executables are installed by their own image
stages. All tracked files, including `flow/scripts`, `flow/util`, platforms,
designs, symlinks, licenses and the tracked `tools/AutoTuner` resources, remain
unchanged. Only `.git` is removed; empty gitlink directories may remain.

Before the final image's existing COPY, the installer writes:

- `ORFS_REVISION`: resolved full ORFS SHA.
- `ORFS_PROVENANCE`: repository URL, resolved SHA and source gitlink SHAs. These
  gitlink SHAs describe omitted upstream sources, **not** the versions of the
  separately installed executables (those remain controlled by the manifest).
- `flow/settings.mk`: upstream's customization hook selecting `openroad`, `sta`
  and `yosys` from runtime PATH. Explicit environment and make command-line
  executable overrides still win. Run make from `flow`, e.g. `make -C "$ORFS_DIR/flow"`.

## Exact upstream audit

Audited [40674dd5cf48db6dc9028d6ab5a98f107208f5bb](https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts/tree/40674dd5cf48db6dc9028d6ab5a98f107208f5bb),
committed 2025-10-25, using a real shallow checkout, `git ls-tree` and a tracked
source search:

| Consumer | Finding |
| --- | --- |
| `.gitmodules:1-9` | Only `tools/OpenROAD`, `tools/yosys`, `tools/yosys-slang` are submodules. None are runtime resources for the standard make flow. |
| `flow/Makefile:1-3` | Includes untracked `settings.mk` before executable defaults. This is used without patching upstream tracked scripts. |
| `flow/scripts/variables.mk:83-124` | Outside Nix, defaults point at `tools/install`, not source submodules. Generated settings select separately installed tools. KLayout already falls back to PATH. |
| `flow/util/genMetrics.py:176-181,208-228` | Git repository probes handle nonzero Git exit statuses; without `.git`, metrics warn and report `not a git repo` / `N/A`. Read `ORFS_REVISION` for provenance instead. The installer does not remove the system Git executable. |
| `env.sh:9-15` | `OPENROAD` names the omitted source directory, and extra PATH entries name upstream build outputs. The image's own runtime environment provides the independently installed executables; do not use `OPENROAD` as a source checkout. |
| `flow/util/docker_shell:28-29` | External Docker helper defaults to upstream tools/install layout; pass `OPENROAD_EXE` / `YOSYS_EXE` when using that helper with a separately provisioned image. Nested Docker is not part of the standard in-image flow. |
| `flow/test/test_delta_debug.sh:14,27` | Developer delta debugging requires `tools/OpenROAD/etc/deltaDebug.py`, deliberately not included. Rebuilding tools and source-dependent developer tests require a separate source checkout. |

Omitted source gitlinks at the audited pin:

- OpenROAD: `83ff25699764e58118fc536056a34326b22cba8f`
- Yosys: `89f32a415b2fcd9fdf08f735fae043fac9e1ab4a`
- yosys-slang: `ccc13eabc333a59d3a78bdb1d4a002928050e92d`

## Validation

Host-only regression tests use real local Git repositories with deliberately
unavailable source submodule URLs, including a builder configuration enabling
recursive submodules. They exercise resource preservation, exact revision
selection when upstream HEAD moves, Git removal, provenance, make executable
selection, and command-line overrides:

```sh
python -m unittest discover -s tests -p test_orfs_runtime.py -v
bash -n images/orfs/install.sh
```

A separate manual run of the installer against the audited upstream checkout
verified all 2,426 tracked non-gitlink files/symlinks were identical and ran the
real upstream Makefile with executable-selection probes. Probe executables were
fixtures: this validates make's selection, **not synthesis or physical design**.
No Docker build or complete physical flow was possible on the development host.
The pre-existing ORFS/Yosys 0.44 incompatibility remains; removing source
submodules does not fix tool-version compatibility.
