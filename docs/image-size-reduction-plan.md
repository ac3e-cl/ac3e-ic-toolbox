# Image size reduction plan

## Scope and evidence

The analysis and line references below describe the baseline before trimming;
some cited SKY files have already been removed in `dev/no-sky`.

### Implementation status in `dev/no-sky`

- General SKY and its private template removed from the single image's composition.
- SKY exclusion is temporary, to analyze space before reintroducing it in a later
  release. Its tests, data and helpers are preserved: regular and full suites
  report them as `EXCLUDED`; adapter host tests use `unittest.skip`.
  They are neither deleted nor counted as passing.
- IHP, GF and global LibreLane retained without changing their revisions.
- ORFS distributed tree no longer downloads source submodules or contains Git history.
- CPython 3.11.18 added under `/opt/python`, with EDA packages in `/opt/eda-venv`
  and user-facing precedence. Ubuntu 22.04 and `/usr/bin/python3` remain intact;
  Nix tools and their isolated interpreters are not replaced.
- Host contracts and syntax verified; image build and execution remain pending.
  The attempt with `BUILD_IMAGE_TAG=isaiash/ac3e-ic-toolbox:dev-no-sky` failed on
  Docker socket permissions before any stages ran. No commits have been created.
  No actual savings from the new build are claimed yet.

The intended result is **one image**, retaining IHP and GF and prioritizing SKY
removal. Per-PDK variants, supplementary images and deferred downloads are not
proposed as substitutes for reducing the distributed image.
The priority criterion is savings on the order of **1 GiB or more per intervention**,
not accumulating cleanups of a few MB. Pins are not changed to slim the image.

The Dockerfile, manifest, PDK and LibreLane installers, runtime configuration
and related contracts/tests were reviewed.

The local Docker daemon was inaccessible: permission denied on its socket and
`sudo -n` requires a password. Therefore, **the local 11 GB image was not measured**.
As an alternative, the OCI manifest and configuration history of the public image
`docker.io/isaiash/ac3e-ic-toolbox:0.2.0`, platform linux/amd64, were inspected:

- Platform manifest: `sha256:340fa40e9953e52d0623a126b38a19faf7541f00e09ff6a20a7394481969d4b4`.
- Configuration: `sha256:b8e85480371741df6418fc9675c376692797fd6a741a0484e719dcaa7fb56977`.
- Recorded creation date: `2026-10-18T14:34:34.937636488Z`.
- Sum of compressed layer blobs: **12 932 857 565 bytes = 12.045 GiB**.

This published reference must not automatically be identified with the local
image mentioned. Decimal GB, GiB, compressed size, visible filesystem size and
cumulative layer size must not be compared as though equivalent.

### Large blocks measured in the registry

| Instruction / content | Compressed GiB | What it establishes |
| --- | ---: | --- |
| Installation of all three LibreLane templates | 5.155 | Largest block; includes Nix environments and private PDKs together, not just SKY. |
| Copy of `/opt/pdks` from `open_pdks` | 2.016 | General SKY and GF together. Does not attribute 2 GiB to SKY alone. |
| Copy of `/opt/OpenROAD-flow-scripts` | 1.869 | Complete ORFS is a real opportunity, not an MB-scale optimization. |
| Global LibreLane installation with Nix | 1.471 | A fourth LibreLane environment in addition to the three template environments. |

These are current layer sizes, **not guaranteed savings from partial cleanup**.
Savings from options sharing Nix are not additive: the store already shares
identical paths; different revisions and derivations may need different paths.

## Template comparison: marginal cost, not sum of sizes

IHP and GF `flake.lock` and `flake.nix` files at the exact `manifest.json` commits
and the global LibreLane lock were downloaded and compared with the repository's
SKY adapter. Equality of `locked` objects, including `narHash`, was verified,
not just input names.

| Input | IHP | GF | SKY | Global |
| --- | --- | --- | --- | --- |
| nixpkgs | `9b696460ac78…` | `9b696460ac78…` | **`b3aad468604d…`** | `9b696460ac78…` |
| nix-eda | `8a8e673d5327…` | `854dd782733d…` | `8f990fb77529…` | `e0126a50c541…` |
| Ciel | `1d2526e67a06…` | `1d2526e67a06…` | `afcb23d36861…` | `6978e6b37970…` |
| devshell | `a67c0f87b63b…` | `a67c0f87b63b…` | `255a2b1725a2…` | `255a2b1725a2…` |

Reproducible sources for this comparison:

- [IHP lock](https://raw.githubusercontent.com/IHP-GmbH/ihp-sg13-librelane-template/23c62045bb212175c20d8186a7ab308e15fba98c/flake.lock).
- [GF lock](https://raw.githubusercontent.com/wafer-space/gf180mcu-project-template/33e4b5ecc9faac82787fa7cb205f08377e27b912/flake.lock).
- [Global lock](https://raw.githubusercontent.com/librelane/librelane/ca6adb1e2982cd75445a68b632d461213d8ca421/flake.lock).
- SKY: `images/librelane/sky/flake.lock` and `flake.nix`.

### What is shared and what is not

**IHP and GF use the same package base**, also used by global LibreLane.
They share exactly the same nixpkgs, Ciel and devshell; their shells request
similar utilities and simulators. This allows identical base derivations to be
shared. It does not demonstrate identical complete closures: they have different
LibreLane and nix-eda revisions. As an additional check, the `nix/klayout.nix`
recipes in both nix-eda revisions have the same Git blob, but `nix/yosys.nix`
differs. Even an identical recipe can produce a different derivation if an input
or overlay changes.

**SKY is the least aligned with the rest:** it uses different nixpkgs, nix-eda
and Ciel revisions. The adapter also forces Python 3.11 and a KLayout 0.29.12
derivation, modifies Yosys/OpenROAD Python wrappers and includes a venv with
Tiny Tapeout-specific requirements (`images/librelane/sky/flake.nix:16-45`
and `bootstrap.sh:18-23`). This adds a second dependency family with less scope
for reuse. SKY is not entirely independent: for example, its devshell matches
the global one, and some paths may be shared.

**Conclusion for choosing the reduction:** SKY is the first removal candidate
because its marginal structural cost is less reusable. Keeping IHP and GF retains
two technologies on a common base. Evidence is insufficient to claim that SKY's
exclusive byte total has already been proven largest: a large GF PDK could alter
the ranking even if its environment shares more packages. The combined 5.155 GiB
layer does not separate the three contributions.

### Measurement needed to finalize the byte ranking

For each template T, obtain its Nix path closure and subtract the union of paths
required by **all other retained roots**, including global LibreLane and Nix
itself. Sum `narSize` for exclusive paths and, separately, bytes in its private
PDK, checkout and venv outside Nix. Do not sum three complete closure sizes or
confuse flake sources with runtime closures.

For SKY, IHP and GF, the report must show total closure, shared bytes, exclusive
bytes, private PDK and auxiliary resources. Measure general SKY removal
separately, since it does not belong to the template. `narSize` compares Nix
content, but the build and its compressed manifest confirm final distributed
savings. This measurement requires access to the existing image/store;
Docker socket permissions are still unavailable and there is no local Nix.

## 1. Remove SKY from the single image, retaining IHP and GF

The priority intervention is to omit Tiny Tapeout SKY together with its adapter,
venv, private PDK and exclusive Nix dependencies. To maximize SKY reduction,
the plan also considers not distributing its general PDK. These are distinct
savings: the first avoids the least-shared environment; the second removes PDK data.

There are currently two independent installations:

- General SKY: `Dockerfile:242-248,258-262,492`; the public link points to Volare
  backing. `images/pdks/install_sky130.sh:24-29` already removes SKY130B and the
  indicated `.build`/`.source` paths. Do not count that cleanup again.
- Private SKY: `images/librelane/install.sh:26-47` creates an adapter, venv, Nix
  environment and Ciel PDK under `/opt/librelane-templates`.

Planned changes, without introducing variant mechanisms:

1. Adjust the supported template set to IHP/GF in the manifest and installer.
   The installer currently requires exactly `ihp`, `gf`, `sky` (`install.sh:12,20`).
2. Remove the SKY installer branch and adapter resources with no remaining
   consumers. Keep IHP/GF private locks and PDKs intact.
3. Make the final `open_pdks` composition independent of `sky130_pdk` and omit
   its backing. Do not remove Magic: it also serves retained PDKs.
4. Exclude SKY from the start of the build. Do not install it and then delete it,
   or run GC in a later layer expecting to recover already distributed layers.
5. Update launcher, inventory, documentation and tests to advertise IHP/GF as
   the supported set. Do not hide failures or claim removed SKY coverage.
6. Validate IHP/GF flows and measure total marginal savings, separating the SKY
   template from the general SKY PDK. Do not attribute the entire three-template
   layer to SKY.

Explicit functional effect: the single image no longer includes SKY PDK support
or ready-to-use Tiny Tapeout SKY. It retains IHP/GF and their isolated environments.
Removal is implemented in code; validation in the built image remains pending.
Do not silently replace private PDKs with general ones: their pins differ.

## 2. Runtime ORFS without build repositories

**Objective:** remove GB-scale source and history currently distributed despite
being unnecessary for using the compiled binaries.

Evidence:

- `images/orfs/install.sh:7-17` clones ORFS and all submodules recursively.
- `images/orfs/install.sh:19-22` leaves `.git` removal commented out.
- `Dockerfile:516` copies the entire tree into the runtime.
- The OpenROAD executable is already installed separately (`Dockerfile:515`),
  as is Yosys (`Dockerfile:514`).
- Upstream Git trees at the exact revisions were inspected: ORFS
  `40674dd5cf48db6dc9028d6ab5a98f107208f5bb` references OpenROAD
  `83ff25699764e58118fc536056a34326b22cba8f`. The tracked blobs in that OpenROAD
  submodule alone total **1.340 logical GiB**, before its `.git` and its own
  submodules. This is not an estimate of compressed size.
- In the main ORFS repository, `flow/platforms` totals 0.738 logical GiB and
  `flow/designs` 0.267 logical GiB. Not all are waste: they contain usable
  platforms and examples.

Planned changes:

1. Review `tools/` and Git usage in supported ORFS targets, not just the synthesis test.
2. Prepare an ORFS distribution tree in its stage without initializing or copying
   OpenROAD, Yosys and yosys-slang build submodules when supported targets use
   installed executables. Retain runtime resources actually referenced by that revision.
3. Exclude Git metadata, including submodule metadata, **before the final COPY**.
   Record SHAs as provenance metadata rather than retaining history.
4. Initially retain Makefiles, `flow/scripts`, `flow/util` and platforms.
   Do not trim libraries by extension. If entire platforms or examples are
   removed, make that a separate functionality decision.

Validation: `tests/digital/test-orfs.sh`, plus a small complete physical flow on
platforms declared supported. The current test only exercises Nangate45 synthesis
and does not validate all ORFS by itself. Measure the new COPY and total delta.

## 3. Global LibreLane: retain initially; evaluate only its exclusive cost

The global profile is installed in `Dockerfile:625-628`, and templates in
`Dockerfile:640-642`. The template launcher executes its own environment and PDK
(`images/librelane/librelane-template:30-37`); it does not need to resolve the
LibreLane command from the global profile.

The plan's baseline policy retains global LibreLane alongside IHP/GF templates
in the same image. Its nixpkgs matches both: its **1.471 GiB** layer does not
equal recoverable GiB on removal, because IHP/GF may need to add some of those
paths. Removal based on gross size is not proposed. Reconsider only if at least
1 GiB of exclusive content is measured and losing the global profile is accepted;
never turn it into another image or replace IHP/GF locks.

Do not try to make Nix binaries share Ubuntu libraries through PATH, PYTHONPATH
or LD_LIBRARY_PATH. Do not unify locks or change versions without separate
compatibility work. Current pinning and isolation are deliberate.

If the global profile is removed, review PATH precedence, Nix activation and
tests currently expecting the global command. Run native digital tests and full
flows for retained templates; respect the documented upstream IHP failure,
without converting it to PASS or disabling DRC to slim the image.

## 4. Nix/PDK leftovers and sources — proceed only after measuring at least 1 GiB

Evidence is insufficient to promise extra GB from a `find ... -delete`.
Investigation must focus inside the measured large blocks:

- General GF explicitly retains backing and source caches
  (`images/pdks/install_gf180mcu.sh:30-38`). Inventory actual sizes and follow
  links transitively before considering anything redundant. GF180D depends on
  A backing; `images/pdks/gf180_integrity.py` and `tests/test_gf_cleanup.py`
  protect exactly that case. Do not delete A/B/C or caches based on names.
- For Nix, identify the union of closures of all remaining profiles/roots:
  Nix profile, global profile, GF/IHP profiles and paths referenced by activation
  scripts. Do not retain removed SKY roots. Compare against the entire store
  and inspect roots and caches.
- Only if at least 1 GiB is genuinely unnecessary, prepare a stage exporting
  required closures, their Nix registration and runtime resources, or install
  and clean within the same RUN. Validate offline activation, arbitrary UIDs
  and continued Nix operation. Do not blindly delete active derivations/sources.
- Running GC in a later layer does not remove bytes from lower layers.
  Do not use `nix-store --optimise` as a substitute for excluding content:
  cross-layer hardlinks do not guarantee smaller distributed blobs.

This phase counts as neither achieved savings nor an approved change until measured.

## Sequence and acceptance criteria

1. **Local baseline:** identify the exact tag/ID of the 11 GB image; measure with
   `docker image inspect`, `docker history --no-trunc`, `du -x`/`du -x --apparent-size`
   without following links twice, and Nix closure queries. Save bytes, platform,
   pins and metric. The remote manifest above is a reference, not a replacement
   for that local baseline.
2. **Per-template attribution:** calculate SKY/IHP/GF marginal cost as described
   above; record the environment and private PDK portions separately.
3. **First change:** exclude private SKY and its environment; measure. Also exclude
   general SKY as the second step of the same reduction; measure separately.
   Verify absence of build dependencies and content, not just public links.
4. **Second change:** runtime-only ORFS, retaining resources in use.
5. **Only with evidence:** GB-scale Nix/PDK leftovers; do not remove global
   LibreLane by default or change IHP/GF compatibility for deduplication.
6. Validate successive revisions of the same product. A temporary validation
   tag is not a distributed variant: the result is one image with IHP/GF.
   Do not overwrite/publish the stable tag before validation. Compare each delta
   and the combined delta using the same metric; do not add estimates.
7. Run static checks, updated contract tests and the integration suite for retained
   capabilities. Explicitly run relevant long flows: not all belong to the regular
   suite. For SKY-dependent layout tests, create equivalent coverage with a
   retained PDK or mark the capability removed; do not claim SKY validation in
   an image without it.
8. Accept size interventions only when the actual delta is on the order of GB
   and declared functionality remains intact. Also record compressed size if
   download/distribution matters.

## Outside the priorities

Do not spend this task replacing Ubuntu with Alpine, removing editors, small docs
or bytecode, or cleaning builders never copied to the runtime. Installers already
clean several temporary files and caches. The IHP copy and subsequent `chown`
each duplicate about **0.152 compressed GiB** in the reference: this is a layering
problem, but fixing that `chown` does not meet the requested threshold. Nor does
`strip` after COPY save what it would have saved before COPY.
These observations do not justify diverting the plan from ORFS, PDKs and LibreLane environments.