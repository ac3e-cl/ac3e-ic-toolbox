# LibreLane: isolated upstream templates with Nix

The image retains global LibreLane and the IHP/GF PDKs under `/opt/pdks`.
SKY130 and the Tiny Tapeout SKY template, adapter, private PDK and environment
are temporarily excluded for image-size analysis, with reintroduction planned
for a later release. SKY tests and their fixtures/helpers remain in the repository
but are skipped in both regular and full suites through `tests/exclusions.json`.
There is one image, not a separate image per PDK.
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

| Key | PDK | Upstream template |
| --- | --- | --- |
| `ihp` | `ihp-sg13g2` | [IHP SG13 LibreLane](https://github.com/IHP-GmbH/ihp-sg13-librelane-template) |
| `gf` | `gf180mcuD` | [wafer.space GF180MCU](https://github.com/wafer-space/gf180mcu-project-template) |

Installed resources are under `/opt/librelane-templates/`: `src/<key>` contains
the upstream checkout, `profiles/<key>` the GC-rooted recorded shell,
`activate/<key>.sh` its activation script, and `pdks/<key>` its
private Ciel root. These PDKs are deliberately separate from `/opt/pdks` and are
not modified by `sak-pdk`. The additional Nix closures and PDKs increase image
size and build/download time.

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
(`ERROR_ON_MAGIC_DRC: False`) and excludes CUP from the KLayout deck.
A passing template flow therefore does not
mean that every possible rule deck passed. The integration tests do not add
`--skip` or use the upstream `nodrc` targets.
The complete GF and IHP template tests are excluded from the habitual suite
under `long_running` in `tests/exclusions.json`. Run `tests/test_all_full.sh`
inside the container to execute only these long flows, or run an individual
template script directly. All physical checks, including GF IR drop, remain
unchanged; no reduced variant is provided. Long-suite reports are in
`tests/run/full/`, separate from habitual suite reports.

Inside an image built from this checkout, with `tests/` mounted at
`/home/designer/tests`:

```bash
bash /home/designer/tests/pdk/librelane-template-ihp.sh

# Optional full GF flow including IR drop (excluded from the suite):
bash /home/designer/tests/pdk/librelane-template-gf.sh
# Run all non-excluded repository integration tests:
bash /home/designer/tests/run_all.sh
# Explicit opt-in: run only the long GF/IHP template flows:
bash /home/designer/tests/test_all_full.sh
```

Compilation/implementation uses `MAX_BUILD_JOBS` (default 2) in these tests.
The suite gives full template tests 14400 seconds each (other tests retain the
900-second default); an explicit `TEST_TIMEOUT` overrides either default.
The tests also set LibreLane's subprocess core limit (`_OPENLANE_MAX_CORES`),
OpenMP thread count, and GF's KLayout worker limits: `--jobs` alone only bounds
LibreLane's executor and does not bound every OpenROAD/STA subprocess.
Run the IHP and GF full-chip tests sequentially on memory-constrained hosts;
thread limits are not memory limits. In a probe of image `0.3.0` on a 16 GiB
host with 4 GiB swap, concurrent runs caused the host OOM killer to terminate
IHP's KLayout filler process at approximately 7 GiB anonymous RSS. LibreLane
reported `Filler Generation: Interrupted (SIGKILL)`, not a DRC result. Check
the host kernel log before attributing a SIGKILL to the template or installer;
retry in isolation rather than disabling fill or physical checks.
Logs, the upstream lock, tool paths, simulation XML and `evidence/result.json`
remain under each test's unique run directory. These checks are integration
coverage, not manufacturing signoff or a substitute for shuttle-specific prechecks.

### Validation status after removing SKY

The prior focused installer-overlay validation is historical evidence,
not validation of the current no-SKY image. That overlay had image ID
`sha256:449ce2eefcaa376d31eada9b744fd098a603e77e0a7164e3d2231f15afe38703`;
GF180 passed its complete flow and IHP was blocked by Magic DRC as described
below. The retained template/LibreLane/PDK pins have not changed.

The rebuilt no-SKY image
`sha256:ea126a1a4c4a209134aad8bf90a21a4074201f20682c87a677f065f773e3c811`
passed the regular integration suite offline: 23 PASS, no failures and seven
existing exclusions. Both local-PDK smoke tests passed with user Python 3.11.
The complete template flows were then executed sequentially and offline:
GF passed, including RTL and gate-level simulation, final metrics and GDS;
IHP completed implementation and LVS but failed with 2701 Magic DRC markers.
No checks were disabled. See [the IHP investigation](ihp-template-drc-investigation.md)
for isolated reproductions and comparison with the previous local image.
Current full-flow evidence is under
`tests/run/librelane-template-gf/run.14Hj6C9W/` and
`tests/run/librelane-template-ihp/run.9FsoK7JP/`;
historical evidence under `tests/run/librelane-template-audit/` is intentionally
gitignored.

### Historical known result for the pinned IHP example

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
