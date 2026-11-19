# Release 0.3.1 — GF180 and acceptance audit

**Status: image built; validation incomplete and release not approved.**
Final results and evidence in [release-0.3.1-validation.md](release-0.3.1-validation.md).
The [GF180 plan](gf180-update-0.3.1-plan.md) defines the full scope.
These notes distinguish integration targets from results actually obtained.

## Target revisions and limits

| Component | Immutable target |
| --- | --- |
| wafer.space GF180 template | 1.6.0 — `d99f6e1ba14e549e80d5d83e113fbd82ed37ed5c` |
| Private GF LibreLane | `99148a9c1e648cdfdb9d7b772481af32e0dfbe8b` |
| Global and private GF PDK | `792ef67037d74c8c51811eab3ce23cf793491296` |
| Global Ciel | 3.1.0 — `e180507a4190462d65cdded4448eb4f7bd2f30fa` |
| Planned GF precheck | 1.7.4 — `9b4e7dab6af073d02b81ecc368069540d2f67db9`; installation and execution require independent evidence |

The new arguments are `CIEL_VERSION`, `CIEL_REPO_COMMIT` and
`GF180_PDK_COMMIT`. Legacy arguments, including `OPEN_PDKS_*` and
`PDK_BUILD_JOBS`, are retained for compatibility, but **do not identify the new
GF artifact** or describe a Volare build. `open_pdks` retains its name as a
stage alias. `pdk_builder` now depends on `builder`, not `magic`:
Ciel downloads and activates the artifact without rebuilding it through Volare.

The public interface remains `/opt/pdks/gf180mcuD`. Copy the complete
Ciel root with its link targets under
`/opt/pdks/ciel/gf180mcu/versions/`; copying only the public link is insufficient.
Do not mix new decks with macros or models from the old open_pdks. The inventory
`tests/run/inventory/tools.json` identifies GF as Ciel and records its resolved
root and expected revision separately from the legacy pin. The historical
`OPEN_PDKS_NAME` key is retained for inventory consumers, with
`legacy_inventory_key: true`, `manager: ciel` and `revision_key: GF180_PDK_COMMIT`;
it does not represent an installation of the old open_pdks.

The templates' private PDKs remain separate under
`/opt/librelane-templates/pdks/<key>`. Preserve their `flake.lock`; do not update
branches or resolve downloads during offline use. Matching PDK names do not
justify interchanging Nix environments or private/global roots.

Selection retains `sak-pdk`/`set_pdk`, IHP as the default and the GF SCL
`gf180mcu_fd_sc_mcu7t5v0`. The `gf180mcu_as_sc_mcu7t3v3` and
`gf180mcu_ocd_sc_rt12t3v3` SCLs are options only where installed and supported:
the former is not fully silicon-verified and the latter is not
silicon-verified. Their presence does not constitute signoff.

## IHP protection and shared tools

The following remain unchanged:

- IHP template `23c62045bb212175c20d8186a7ab308e15fba98c`.
- Private IHP LibreLane `c5b5099e55f4e3bed507f2e79441ecfd6432d65c`.
- Private IHP PDK `7bbb4b5a5b64c446fedc64eacadc33fa65ade276`.
- Global IHP PDK `cfc0e22b92306178ebb5a5bc4865afe3294654d0`.

Contracts preserve the historical baseline and allow only the three
Ciel/GF additions and the three GF template revision changes. Other pins,
including global LibreLane, remain protected; any additional shared change
requires justification and an explicit exception, not baseline regeneration.
Frozen pins do not demonstrate compatibility of the rebuilt runtime.

The historical IHP failure with 2701 Magic DRC markers is documented in the
[IHP investigation](ihp-template-drc-investigation.md). It is not a 0.3.1 result
or permission to skip rules or publish a regression. Repeat the flow and compare
evidence; a failure must not be recorded as PASS.

## Acceptance gates (pending until evidence is supplied)

| Gate | Required evidence | What it does not establish |
| --- | --- | --- |
| Host contracts | unittest output, exact GF pins, frozen IHP, Ciel graph and no GF Volare | Do not run EDA or validate downloaded artifacts |
| Syntax and Docker | `bash -n`, `git diff --check`, check with wrapper arguments | Do not build an image |
| GF stage | Persistent `gf180_pdk` log, Ciel version/path and active revision | Does not validate the final runtime or IHP |
| Final image | Exact ID/digest, inventory, valid links and analog resources | Is not equivalent to the full suite |
| Regular offline suite | `tests/run_all.sh`, summary without non-excluded failures | Excludes long flows; exclusions are not passes |
| Global GF | ngspice MOSFET, KLayout PCells, extraction and LibreLane smoke test | Does not validate the private template |
| Full templates | RTL → implementation → nonempty metrics/GDS → GL, GF and IHP sequentially | Does not replace precheck or signoff |
| Precheck 1.7.4 | Own environment, private PDK, positive and negative cases with verified exits | A negative fixture does not validate manufacturing |
| New rules | Fixtures and results for DCF.1a, DF.11, CO.5a/b, LDMOS and filler | Presence of decks does not prove fixes |
| IHP regression | Analog, KLayout, extraction, template and IHP → GF → IHP switching | Identical pins do not prove absence of contamination |

Host commands from the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
bash -n build/*.sh images/*/install.sh images/final_structure/{configure,install}/*.sh tests/*.sh tests/*/*.sh
CHECK_ONLY=1 ./build/build-image.sh
git diff --check
# Real build: preserve logs; do not treat it as a static check.
MAX_BUILD_JOBS=2 ./build/build-stage.sh gf180_pdk
```

After building the final image, mount `tests/` at `/home/designer/tests`
and run inside **that image**, with separate designs and output in `tests/run/`:

```bash
bash /home/designer/tests/run_all.sh
bash /home/designer/tests/test_all_full.sh
```

Record baseline and candidate IDs, architecture, inventories, commands, exit
codes, exclusions and log paths separately. Repeat long flows sequentially on
memory-constrained hosts; do not disable IR drop, filler or DRC to obtain success.
The mere existence of these notes does not establish that any build, container
test or precheck passed.

## Publication and rollback

Do not publish until acceptance blockers are resolved or explicitly documented
with results from the final combination. The publication branch would be
`release/0.3.1`, with a matching `release.version`; creating or pushing it is
not part of this preparation. Regular CI does not replace the long-flow and
precheck gates above. Preserve the previous image by ID and its pins; do not
delete PDKs, designs or caches to force the migration. If GF or IHP regress,
stop publication, fix or isolate the incompatibility and repeat affected gates.
