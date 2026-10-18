# LibreLane: isolated upstream templates with Nix

The global toolbox LibreLane installation and `/opt/pdks` remain unchanged.
For template work, use `librelane-template`, which selects a separately recorded
Nix development shell and PDK root. Do not combine these templates with the
global LibreLane executable or the analog PDKs merely because the PDK names match.

## Installation policy

Follow the [official Linux Nix instructions](https://librelane.readthedocs.io/en/latest/installation/nix_installation/installation_linux.html):
Nix, flakes, and the FOSSi binary cache are required. The Docker image already
installs Nix in single-user mode (a container-specific adaptation of the official
installer, which normally configures a daemon). Do not install Nix from Ubuntu's
`apt` repositories or nest another Docker engine inside this image.

The existing settings enable `nix-command flakes`, the FOSSi substituter
`https://nix-cache.fossi-foundation.org`, and its signing key
`nix-cache.fossi-foundation.org:3+K59iFwXqKsL7BNu6Guy0v+uTlwsxYQxjspXzqLYQs=`.
The global LibreLane source remains pinned by `build.arguments` in `manifest.json`.

`manifest.json` also records the immutable template commits and their PDK and
LibreLane revisions under `librelaneTemplates`. The image build fetches those
commits recursively, preserves IHP/GF's upstream `flake.lock`, and records each shell
using `nix develop --profile` and exports its activation with `nix print-dev-env`.
Runtime commands source that recorded environment and execute its shell hook;
they do not invoke Nix, download packages, update locks or replace the global
Nix profile. This also supports arbitrary numeric UID/GID launchers: running
`nix develop` itself would require write access to this single-user Nix database.

SKY has no upstream Nix flake. Its adapter under `images/librelane/sky/` pins
LibreLane **3.0.14** to the revision selected by the template's `ttsky26d` GDS
action, including that LibreLane revision's Nix inputs. It builds LibreLane with
Nix for Python 3.11 and installs the unchanged support-tools/test requirements in
a private venv; **LibreLane itself is not installed with pip**. Python 3.11 is
needed for support-tools' `numpy==1.26.4`. The binding KLayout wheel is hash-pinned
as a Nix derivation; Yosys and OpenROAD retain their separate embedded-Python
dependencies. The bootstrap exercises imports in both embedded interpreters,
not just in the LibreLane venv.
The venv is intentionally not relocatable; install it at its final image path.
The SKY adapter currently targets **x86_64 Linux**. Its private compatibility
requirements pin cryptography 45.0.7 to satisfy upstream's cffi 1.17.1 and add
wheel 0.45.1 for libparse; `pip check` must pass before installation succeeds.

| Key | PDK | Upstream template |
| --- | --- | --- |
| `ihp` | `ihp-sg13g2` | [IHP SG13 LibreLane](https://github.com/IHP-GmbH/ihp-sg13-librelane-template) |
| `sky` | `sky130A` | [Tiny Tapeout SKY Verilog](https://github.com/TinyTapeout/ttsky-verilog-template) |
| `gf` | `gf180mcuD` | [wafer.space GF180MCU](https://github.com/wafer-space/gf180mcu-project-template) |

Installed resources are under `/opt/librelane-templates/`: `src/<key>` contains
the upstream checkout, `profiles/<key>` the GC-rooted recorded shell,
`activate/<key>.sh` its activation script, and `pdks/<key>` its
private Ciel root. These PDKs are deliberately separate from `/opt/pdks` and are
not modified by `sak-pdk`. The additional Nix closures and PDKs increase image
size and build/download time.
SKY uses `sky-env/nix` as its rooted Nix package environment and `sky-env/venv`
for support-tools; its adapter lock is kept under `sky/flake.lock` rather than
inventing an upstream template lock.

## Use inside the container

Create a writable design copy in the persistent user workspace:

```bash
librelane-template init ihp /foss/designs/ihp-example
librelane-template run ihp /foss/designs/ihp-example make sim
librelane-template run ihp /foss/designs/ihp-example make librelane
librelane-template run ihp /foss/designs/ihp-example make sim-gl

librelane-template init gf /foss/designs/gf-example
librelane-template run gf /foss/designs/gf-example make sim
librelane-template run gf /foss/designs/gf-example make librelane
librelane-template run gf /foss/designs/gf-example make sim-gl

librelane-template init sky /foss/designs/sky-example
librelane-template run sky /foss/designs/sky-example bash -c 'cd test; make'
librelane-template run sky /foss/designs/sky-example python tt/tt_tool.py --create-user-config
librelane-template run sky /foss/designs/sky-example python tt/tt_tool.py --harden --no-docker
librelane-template run sky /foss/designs/sky-example python tt/tt_tool.py --create-tt-submission
```

`init` refuses to overwrite an existing directory. Omit the command after the
project directory to open the selected shell. The launcher clears inherited
`BASH_ENV`, `PYTHONPATH`, `LD_LIBRARY_PATH`, PDK and SCL settings before entering
Nix, then explicitly selects the template's private `PDK_ROOT` and `PDK`.
This is dependency isolation, not a security sandbox: template code is trusted.

IHP follows its upstream full-chip `librelane/config.yaml`, default SG13G2 variant,
and pinned Ciel PDK. GF follows its default `1x1` slot, 5 V SRAM configuration,
`gf180mcu_fd_sc_mcu7t5v0` SCL and `gf180mcu_fd_io` pads. Optional upstream variants
are not covered by the default integration tests.

For SKY, support-tools is checked out under `tt/` at the manifest-pinned commit,
not its floating `main` branch. `--no-docker` uses the Nix-provided toolchain
directly. `--harden` deletes its previous `runs/wokwi` output, as upstream does.
Before normal use, fill the empty title, author and description in `info.yaml`.
Integration tests fill only these metadata fields with explicit test labels in
their disposable copy; the installed template and upstream RTL remain unchanged.
For gate-level testing, copy `tt_submission/<top_module>.v` to
`test/gate_level_netlist.v`, select `PDK_ROOT` from `runs/wokwi/resolved.json`,
then run `make GATES=yes` and `python -m cocotb_tools.check_results results.xml`
inside `test/`. The integration test automates this and verifies both XML reports.

## Integration tests

The standard `make build` includes the template installer in the final image.
For focused installer validation without recompiling unrelated EDA tools, build
an overlay on an existing toolbox image from the repository root:

```bash
docker build -f images/librelane/Dockerfile \
  --build-arg TOOLBOX_IMAGE=isaiash/ac3e-ic-toolbox:0.1.0 \
  --build-arg MAX_BUILD_JOBS=2 -t ac3e-librelane-templates-check .
```

This exercises the same installer but is not a complete source-image rebuild.

Tests copy templates into `tests/run/`, never `shared/`. Each test must pass RTL
simulation, the full implementation flow with the upstream verification policy, final nonempty
metrics and GDS checks, and gate-level simulation. XML reports are checked for
failures, errors, skipped tests, and empty results; successful command exit alone
is not enough.

The verification policy is intentionally not strengthened silently: IHP disables
`Checker.IllegalOverlap`; GF runs Magic DRC but treats its violations as advisory
(`ERROR_ON_MAGIC_DRC: False`) and excludes CUP from the KLayout deck; Tiny Tapeout
disables KLayout DRC and XOR in its generated configuration and runs its shuttle
precheck separately in upstream CI. A passing template flow therefore does not
mean that every possible rule deck passed. The integration tests do not add
`--skip` or use the upstream `nodrc` targets.
The complete GF, IHP and SKY template tests are excluded from the habitual suite
under `long_running` in `tests/exclusions.json`. Run `tests/test_all_full.sh`
inside the container to execute only these long flows, or run an individual
template script directly. All physical checks, including GF IR drop, remain
unchanged; no reduced variant is provided. Long-suite reports are in
`tests/run/full/`, separate from habitual suite reports.

Inside an image built from this checkout, with `tests/` mounted at
`/home/designer/tests`:

```bash
bash /home/designer/tests/pdk/librelane-template-ihp.sh
bash /home/designer/tests/pdk/librelane-template-sky.sh
# Optional full GF flow including IR drop (excluded from the suite):
bash /home/designer/tests/pdk/librelane-template-gf.sh
# Run all non-excluded repository integration tests:
bash /home/designer/tests/run_all.sh
# Explicit opt-in: run only the long GF/IHP/SKY template flows:
bash /home/designer/tests/test_all_full.sh
```

Compilation/implementation uses `MAX_BUILD_JOBS` (default 2) in these tests.
The suite gives full template tests 14400 seconds each (other tests retain the
900-second default); an explicit `TEST_TIMEOUT` overrides either default.
The tests also set LibreLane's subprocess core limit (`_OPENLANE_MAX_CORES`),
OpenMP thread count, and GF's KLayout worker limits: `--jobs` alone only bounds
LibreLane's executor and does not bound every OpenROAD/STA subprocess.
Logs, the upstream lock, tool paths, simulation XML and `evidence/result.json`
remain under each test's unique run directory. These checks are integration
coverage, not manufacturing signoff or a substitute for shuttle-specific prechecks.

### Completed local validation

Local image: `ac3e-librelane-templates-check:latest`, image ID
`sha256:449ce2eefcaa376d31eada9b744fd098a603e77e0a7164e3d2231f15afe38703`.

| Template | RTL | GDS | Gate-level | Full-flow result |
| --- | --- | --- | --- | --- |
| SKY | PASS | Decoded successfully | PASS | PASS under the upstream verification policy |
| GF180 | PASS | Decoded successfully | PASS | PASS; zero Magic DRC, KLayout DRC and LVS errors |
| IHP | PASS | Decoded successfully | PASS | BLOCKED upstream: 2701 Magic DRC markers |

SKY and GF180 completed end-to-end on this final image. The IHP full flow was
run in its isolated, identically pinned Nix environment; its RTL/gate-level
tests and GDS decoding were repeated on the final image. All three installed
environments also passed activation, PDK access and writable-project probes
with numeric UID/GID `12345`, without writable access to the Nix store.

This is focused installer-overlay validation, not a full source rebuild of the
entire toolbox. The machine-readable result is
`tests/run/librelane-template-audit/summary.json`; complete per-run outputs
remain under `tests/run/librelane-template-{sky,gf}/` and the IHP evidence
directory below. Generated evidence is intentionally gitignored.

### Known result for the pinned IHP example

With the manifest-pinned IHP template, LibreLane and PDK, the full example flow
produced GDS and final metrics but **failed with 2701 Magic DRC errors**.
The same run reported zero KLayout DRC errors and zero LVS errors; RTL and
gate-level simulation passed, including re-execution with the built validation
image. These results are not equivalent to a clean signoff. The integration
test deliberately retains the upstream failure instead of suppressing Magic DRC
or silently changing the template/PDK pins.

The Magic report contains the following marker counts (markers are not
necessarily independent physical defects):

| Category | Markers |
| --- | ---: |
| Wide/long TopMetal2 spacing, `TM2.bR` | 624 |
| Subcell abutment/partial overlap | 1792 |
| N-diffusion contact enclosure, `Cnt.c` | 54 |
| Prohibited layer overlap | 82 |
| SRAM contact enclosure exception | 149 |
| **Total** | **2701** |

The template's PDN uses 6 µm-wide straps with 2 µm spacing, conflicting with
the 5 µm spacing recommendation for lines wider than 5 µm with parallel runs
longer than 50 µm. Magic's full deck applies `TM2.bR`; this run's KLayout
command uses the PDK default `no_recommended=true`, so its zero count does not
clear the Magic markers. Pad/SRAM marker adjudication also requires agreement
between the library geometry and the differing verification decks.

The pinned [upstream CI](https://github.com/IHP-GmbH/ihp-sg13-librelane-template/blob/23c62045bb212175c20d8186a7ab308e15fba98c/.github/workflows/ci.yml)
implements with `make librelane-nodrc`, not the complete DRC flow used here.
The installation policy is to **retain the upstream template and checks intact
and report IHP full-chip signoff as blocked upstream**. No PDN correction,
waiver or revision change is applied by this toolbox.

Generated evidence is kept under `tests/run/librelane-template-audit/ihp/`.
The built validation image is a focused overlay, not a complete source rebuild
of every EDA tool. Its exact ID, template/PDK revisions and installed-code hashes
are recorded under `tests/run/librelane-template-audit/`.
