# Global GF180: Ciel artifact integration

The global installer consumes `CIEL_VERSION=3.1.0`,
`CIEL_REPO_COMMIT=e180507a4190462d65cdded4448eb4f7bd2f30fa` (installed by
Docker), `GF180_PDK_COMMIT=792ef67037d74c8c51811eab3ce23cf793491296`, and an
explicit `PDK_ROOT`. It downloads data, not architecture-specific executables;
Magic is not needed to download or patch this artifact. There is no legacy
build/download fallback.

## Audited upstream sources

- [Ciel source](https://github.com/fossi-foundation/ciel/tree/e180507a4190462d65cdded4448eb4f7bd2f30fa):
  `pyproject.toml`, `families.py`, `manage.py`, `source.py`.
- [GF180 release](https://github.com/fossi-foundation/ciel-releases/releases/tag/gf180mcu-792ef67037d74c8c51811eab3ce23cf793491296)
- [Artifact manifest](https://fossi-foundation.github.io/ciel-releases/gf180mcu/792ef67037d74c8c51811eab3ce23cf793491296/manifest.json)

The manifest contains `common.tar.zst` and 15 library archives. The downloaded
common archive includes Xschem symbols/config, ngspice models, Magic technology,
Netgen support, LibreLane config, KLayout technology/rules/PCells/macros and
upstream license headers. No old fd_pr checkout or deck overlay is needed.
Ciel's GF family maps to open_pdks upstream; this artifact revision is **not**
a replacement value for a legacy `OPEN_PDKS_REPO_COMMIT` build argument.

Ciel installs backing under `ciel/gf180mcu/versions/<revision>/`. Copy the whole
root, not just the public `gf180mcuD` symlink. Only public A/B/C links are hidden;
private variants/resources remain available. The integrity helper validates
current revision, the public link, required analog resources, all 15 libraries
and recursively checks symlinks through linked directories.

## Minimal runtime adaptations

The new KLayout layout is `libs.tech/klayout/tech/{pymacros,macros,drc,lvs}`.
The patch adds relative compatibility aliases at `klayout/` without moving or
copying rule decks. It keeps upstream dbu/connectivity; only the technology name
is changed to `gf180mcuD` for the existing selector contract. The old custom
technology rewrite is restricted to legacy installations.

The gdsfactory PCell package still needs local generic-PDK activation with the
installed gdsfactory 7 API. Both gdsfactory and native KLayout PCell backends
contain hard-coded efuse paths: these are changed to module-relative paths,
retaining the original source and license headers. Xschem paths and GUI option
D defaults are adapted offline. The legacy patch branch remains solely for
compatibility, never as an installation fallback.

`gf180mcu_fd_sc_mcu7t5v0` remains the default. New libraries are opt-in:
`gf180mcu_as_sc_mcu7t3v3` is not fully silicon-verified;
`gf180mcu_ocd_sc_rt12t3v3` is not silicon-verified. Presence is not signoff.

## Validation limits

Host fixtures cover structure, idempotence, legacy OverlayFS/EXDEV moves,
missing resources, broken links and version mismatch. They do not validate
fabrication rules or substitute for the final-image GF/IHP tests.

LibreLane global commit `ca6adb1e2982cd75445a68b632d461213d8ca421`
already recognizes `libs.tech/librelane/config.tcl`, per-SCL configs and
`CELL_LIBS`. This source inspection alone does not prove compatibility with
the new artifact. Execute the existing full GF counter smoke flow, plus IHP
regressions, before deciding whether a shared LibreLane upgrade is necessary.
Templates/precheck retain their own independently locked environments.
