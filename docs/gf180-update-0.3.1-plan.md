# GF180 update plan — dev/0.3.1

## Objective and scope

Update the wafer.space template to 1.6.0, its PDK and its LibreLane, and add
GF180 Precheck 1.7.4. Migrate the general-purpose GF180 installation from Volare
to Ciel 3.1.0 and update its PDK without changing the IHP PDK, template or
LibreLane environment.
This document is a plan: it does not represent an already implemented update.

## Revisions verified upstream

| Component | Current | Target |
| --- | --- | --- |
| GF template | `33e4b5ecc9faac82787fa7cb205f08377e27b912` | tag `1.6.0`, commit `d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c` |
| Private GF LibreLane | `df37e133fc3426c16e8356b1f50a17f8d6082f60` | `99148a9c1e648cdfdb9d7b772481af32e0dfbe8b` |
| Private GF PDK | `f6eeac7dad085ffcc829ccfd721f7b4ce39edcf7` | `792ef67037d74c8c51811eab3ce23cf793491296` |
| GF precheck | No integration found in the repository | tag `1.7.4`, commit `9b4e7dab6af073d02b81ecc368069540d2f67db9` |
| GF PDK manager | Volare `0.18.1` for global GF | Ciel `3.1.0`, commit `e180507a4190462d65cdded4448eb4f7bd2f30fa` |

Sources consulted: Git refs from the wafer.space repositories, and `Makefile`
and `flake.lock` at both target commits. Template and precheck declare the same
PDK and LibreLane commit. Preserve their locks; do not resolve their floating
branches (`leo/update-pdks` and `dev`) or regenerate locks.

- https://github.com/wafer-space/gf180mcu-project-template/tree/d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c
- https://github.com/wafer-space/gf180mcu-precheck/tree/9b4e7dab6af073d02b81ecc368069540d2f67db9

### Ciel verified for wafer.space 1.6.0

The template's `flake.lock` resolves `librelane.inputs.ciel` to tag `3.1.0`,
commit `e180507a4190462d65cdded4448eb4f7bd2f30fa`. That commit's `pyproject.toml`
declares `version = "3.1.0"` and Python `>=3.8`. The precheck 1.7.4 lock resolves
exactly the same Ciel. This checks sources and Nix resolution, not execution of
the binary: confirming `ciel --version` in the materialized environment and
recording its path are implementation gates.

Additional sources:
- https://github.com/wafer-space/gf180mcu-project-template/blob/d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c/flake.lock
- https://github.com/fossi-foundation/ciel/blob/e180507a4190462d65cdded4448eb4f7bd2f30fa/pyproject.toml

## IHP protection invariants

Do not modify:

- `librelaneTemplates.ihp`, including its PDK `7bbb4b5a5b64c446fedc64eacadc33fa65ade276`
  and LibreLane `c5b5099e55f4e3bed507f2e79441ecfd6432d65c`.
- The global `IHP_PDK_REPO_COMMIT` pin:
  `cfc0e22b92306178ebb5a5bc4865afe3294654d0`.
- IHP's default selection and patches/installers, except for minimal, justified
  compatibility adaptations covered by tests.
- `/opt/pdks/ihp-sg13g2` or the IHP template's private resources.

Global LibreLane and shared tools may be updated when a GF requirement is
established. IHP protection shifts from freezing all tools to preserving its
PDKs and validating operation with the new versions. Absence of declared
restrictions does not demonstrate compatibility.

Rebuilding shared layers does not guarantee identical binaries when dependencies
float. Record inventories and validate IHP in the resulting image, in addition
to checking pins.

## Phase 1 — Baseline and global PDK migration to Ciel

1. Capture an inventory of a baseline image identified by ID: pins, versions,
   link targets, resources and available GF/IHP test results.
2. Confirm the repository/family and Ciel artifacts corresponding to commit
   `792ef67037d74c8c51811eab3ce23cf793491296`; review structure, library manifests,
   analog support, licenses and compatibility with installed KLayout, Xschem,
   ngspice and Magic.
3. Replace the GF Volare/open_pdks build with download and activation through
   Ciel 3.1.0 during the build. Do not replace the old open_pdks pin
   `0fe599b2afb6708d281543108caf8310912f54af` with the new PDK commit:
   record separate Ciel and GF artifact pins in the manifest.
4. Use the upstream command as a reference, with an explicit global root:
   `ciel enable 792ef67037d74c8c51811eab3ce23cf793491296 --pdk-root /opt/pdks --pdk gf180mcuD --include-libraries all`.
   Verify artifact availability for the target architecture and preserve the
   complete Ciel root and required links when copying to the runtime. Retain
   `/opt/pdks/gf180mcuD` as the public interface and independent private roots.
   If analog resources are missing or compatibility fails, record the blocker
   and resolve it before accepting the migration; do not hide it with a Volare fallback.
5. Do not copy new decks over old libraries without checking their compatibility
   matrix. Do not blindly apply the current open_pdks patch to Ciel.

## Phase 1B — Shared tools and compatibility matrix

1. Compare new GF requirements with current global versions and the dependencies
   pinned in IHP/GF locks. Record each tool's current version, immutable target,
   rationale, consumers and required tests. Review KLayout, Magic, ngspice,
   Xschem, Netgen, Python and LibreLane according to actual dependencies;
   do not assume all need an update.
2. Change only necessary tools, one at a time or in inseparable dependency
   groups. Do not automatically choose the latest version or assume template
   LibreLane can replace the global installation without reviewing its setup.
3. Preserve both templates' private locks and environments. A global update must
   not replace their Nix executables or inject Python packages or libraries
   through inherited variables. Verify the executable and version resolved in
   each context, including tools that invoke absolute paths.
4. After each shared change, build its stage and run quick GF and IHP regressions
   in a runtime that actually contains the change. Validate both full flows with
   the final combination before accepting the image.
5. If IHP regresses, investigate and minimally adapt the integration without
   changing its PDK. If no compatible common version is available, retain
   isolated versions per environment; do not sacrifice IHP to unify versions.
6. Extend manifest contracts with an explicit list of authorized shared changes.
   Keep remaining pins frozen and record inventory differences and results
   against the baseline.

## Phase 2 — Isolated template and precheck

1. Update only `librelaneTemplates.gf` in `manifest.json` with the three target
   commits. Retain `gf180mcuD` and upstream defaults.
2. Validate the installer against the new Makefile and lock. Install all required
   libraries: upstream now uses `--include-libraries all`.
3. Record the precheck pin explicitly in the manifest and implement its
   installation and GF-only launcher. No current integration can be updated
   simply by changing a version.
4. Materialize the precheck's Nix environment from ITS lock; reuse an environment
   only if compatibility of its complete dependencies is demonstrated, not
   merely because the LibreLane commit matches.
5. Run precheck with its private GF PDK, sanitized environment, explicit
   parameters and output in the project or `tests/run/`. Do not download or
   update locks at runtime. Preserve arbitrary UID/GID support in current launchers.
6. Update global LibreLane only if a global GF flow requires it and IHP regressions
   pass; template and precheck retain their private environments.

## Phase 3 — Global GF PDK and libraries

1. Rewrite `images/pdks/install_gf180mcu.sh` to use Ciel instead of
   `volare build`/`volare enable`. Review the `gf180_pdk` stage, its arguments,
   dependencies, copies and metadata. Do not run `prepare_open_pdks` or extract
   macros from the old fd_pr to automatically complete the new PDK.
   Audit the Ciel artifact's resources and adapt only what is necessary.
2. Install Ciel 3.1.0 reproducibly in the build environment and, if exposed to
   users, in a controlled, compatible runtime environment. Record version and
   commit in the manifest; verify `ciel --version` and the effective path.
   Audit Python dependencies before changing common packages. Templates retain
   Ciel from their own locks, including IHP.
3. Audit all Volare consumers, including `images/base/python_packages.sh`,
   `images/builder/exhaustive-install.sh`, `images/pdks/prepare_open_pdks.sh`,
   `gf180_integrity.py`, Dockerfile, inventory and contracts. Remove dependencies
   and helpers only when they have no remaining consumers; do not globally
   replace `volare` strings that remain valid.
4. Adapt the integrity check to the actual `ciel/gf180mcu/versions/` structure
   and verify links without assuming the old installation's A backing.
   Preserve required private resources; do not accidentally expose extra variants.
5. Retain `set_pdk gf180mcuD`/`sak-pdk gf180mcuD`, the current default SCL and
   IHP selection. New libraries are options, not default changes.
6. Verify presence and explicit selection of `gf180mcu_as_sc_mcu7t3v3` and
   `gf180mcu_ocd_sc_rt12t3v3` in environments that support them. Document that
   the former is not fully silicon-verified and the latter is not silicon-verified;
   do not present these options as validated signoff.
7. Review current GF patches: PCell structure, gdsfactory activation, efuse,
   macros, variants and Xschem paths. Remove/adapt only what applies to the new
   upstream; test idempotence and behavior across Docker layers.

## Phase 4 — Tests and gates

### Host contracts and static checks

- Introduce tests that fail with the old pins and pass with the targets;
  explicitly enforce IHP invariants and environment isolation.
- Adapt `tests/test_librelane_templates.py` and
  `tests/test_repository_contract.py`: they currently require GF pins to match
  the baseline. Do not bulk-update the baseline or remove IHP protection.
- Test argv, exit code and absence of downloads in the precheck launcher.
- Add Ciel installation contracts: exact version, GF commit, explicit root,
  all libraries, valid links and no Volare invocations in the GF installer.
  Update inventory: do not identify new GF as old open_pdks. Test offline
  operation with preinstalled PDKs.
- Run host contracts, `bash -n`, Docker check with wrapper-resolved arguments
  and `git diff --check`.

### Real builds and tests

1. First build the affected GF stage and/or template overlay, with bounded jobs
   and persistent logs. This does not replace the final image.
2. Build the final image and record its ID. Mount tests separately from designs;
   write results in `tests/run/`, never over user work.
3. Global GF: environment, SCL selection, links, ngspice MOSFET, KLayout PCells,
   extraction/layout and LibreLane smoke test compatible with the chosen installation.
4. GF template: RTL, full implementation, nonempty metrics and GDS, and gate-level
   simulation. Retain IR drop and upstream policy; do not omit checks to force success.
5. Precheck 1.7.4: run on a compatible design and add a negative case with a
   verified error exit. A fixture expected to fail does not validate signoff.
6. New rules: find and exercise upstream fixtures for DCF.1a, DF.11, CO.5a/b,
   LDMOS extraction and filler; record results. File presence or the pin alone
   does not prove those fixes.
7. IHP: selection, analog simulation, KLayout, extraction and full template
   RTL → GDS → GL; repeat IHP → GF → IHP switching in the same shell to detect
   variable/path contamination. Use existing tests and add missing tests after
   reviewing actual coverage.
8. Confirm long flows excluded from `make test` are run explicitly; do not
   confuse the regular suite with full validation.

## Acceptance criteria

- GF template 1.6.0 and precheck 1.7.4 installed and exercised with exact pins.
- Global GF installed through Ciel 3.1.0 at the target commit, without a Volare
  build or silent mixing of old resources; normal commands work offline and
  links are valid in the final image.
- Target GF PDK verified in updated environments. Report global and private
  status separately; any global blocker remains pending, not declared resolved.
- No IHP PDK or template pin changes. Every shared update is justified and
  pinned; IHP and GF tests pass in the new image without contamination when
  switching PDKs. Contracts allow only authorized changes.
- New SCLs available where applicable, opt-in and with silicon warnings.
- Documentation updated for versions, paths, commands and validation limits.
- Delivery includes image IDs, inventories, logs and real results, distinguishing
  static checks, partial builds, final image and manufacturing signoff.

## Rollback

Preserve the previous image by ID and its previous pins. Do not delete caches or
PDKs from the baseline image to recover space without approval. If GF or IHP
fails, do not publish: revert or isolate the incompatible shared tool, or fix
the integration and repeat affected gates. Also revert GF changes where
appropriate; keep a record of the validated version combination.
Do not commit, push or publish without an explicit request.