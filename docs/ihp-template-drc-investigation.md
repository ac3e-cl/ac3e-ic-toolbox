# IHP template: Magic signoff blocker

## Outcome

The pinned upstream template is **not clean under its pinned Magic full DRC**.
Do not waive these errors, disable checks, or describe the successful LVS and
zero-error KLayout result as complete signoff. No production geometry, rule,
check, or revision was changed during this investigation. No full flow was
repeated. A complete correction has not been established.

Image tested: `isaiash/ac3e-ic-toolbox:0.3.0`, image ID
`sha256:ea126a1a4c4a209134aad8bf90a21a4074201f20682c87a677f065f773e3c811`.
Template: `23c62045bb212175c20d8186a7ab308e15fba98c`;
PDK: `7bbb4b5a5b64c446fedc64eacadc33fa65ade276`;
LibreLane: `c5b5099e55f4e3bed507f2e79441ecfd6432d65c`.

## Baseline and coordinate attribution

Evidence root, relative to the repository:

```
tests/run/librelane-template-ihp/run.9FsoK7JP/project/
```

The existing `evidence/flow.log` finishes 82/82 stages, reports LVS PASS,
KLayout DRC 0 and Magic DRC 2701, and exits with a deferred Magic DRC error.
Programmatic parsing of
`librelane/runs/template/67-magic-drc/reports/drc.magic.rpt` accounts for every
marker:

| Magic category | Markers | Marker-midpoint attribution |
| --- | ---: | --- |
| TM2.bR wide/long metal spacing | 624 | 412 top/PDN/fill; 212 within SRAM bounding boxes |
| Partial overlap/abutment between subcells | 1792 | 896 output pads; 896 bidirectional pads |
| Cnt.c N-diffusion contact enclosure | 54 | SRAMs only |
| Incompatible layer overlap | 82 | 33 output, 41 bidirectional, 4 IOVdd, 4 Vdd pad regions |
| Cnt.c SRAM-exception enclosure | 149 | SRAMs only |
| **Total** | **2701** | |

Attribution is spatial, not proof that the macro caused every marker inside its
bounding box: top-level PDN also crosses the SRAMs. The JSON preserves every
marker, cell bounding box and instance transform.

SRAM placements read directly from the checkpoint GDS:

- `i_chip_core.sram_0`: transform `r0 *1 390,390`, bounding box
  `(390,389.775)-(806.64,726.46)`; 27 Cnt.c and 81 SRAM-exception markers.
- `i_chip_core.sram_1`: transform `r270 *1 860,806.64`, bounding box
  `(859.775,390)-(1196.46,806.64)`; 27 Cnt.c and 68 SRAM-exception markers.

## Root-cause probes, with all Magic full rules retained

### PDN violates the wide/long TM2 spacing rule

The upstream config explicitly sets `PDN_HWIDTH: 6` and `PDN_HSPACING: 2.0`.
Two **actual top-level polygons** on GDS layer `134/0`, extracted from
`librelane/runs/template/64-klayout-filler/chip_top.gds`, are:

```
(345.78,1133.66)-(1254.06,1139.66)
(325.78,1141.66)-(1274.06,1147.66)
```

Both are 6 micrometres wide, separated by 2 micrometres over more than
50 micrometres. Pinned `libs.tech/magic/ihp-sg13g2-drc.tech:748` applies
`widespacing ... 5000` for widths above 5 micrometres and parallel lengths above
50 micrometres: **5 micrometres spacing**, not 2. The printed `< 1000` in the
Magic message is an internal-unit substitution, not a 1000-micrometre limit.

Running the two polygons alone with pinned Magic and `drc(full)` gives four
TM2.bR markers. Moving only the second polygon by 3 micrometres, producing
5-micrometre spacing, gives zero markers with identical rules. This is a
red/green geometry probe, **not** a corrected full-chip GDS. Changing the PDN
spacing globally is not yet safe: the upstream configuration intentionally
matches the SRAM PDN, so macro connectivity must be revalidated.

### Pad overlaps include a hierarchy/import artifact

The unmodified PDK `sg13g2_io.gds`, checking `sg13g2_IOPadOut30mA` alone with
the template's exact SRAM flatglob list, reproduces 112 partial-overlap markers
and two incompatible-layer markers. Eight output pads account exactly for
896 baseline partial-overlap markers.

A differential probe changes only `gds flatglob *` before reading the same IO
GDS: the isolated pad becomes **zero errors**, with full rules still enabled.
Flattening is therefore a credible import correction, not a waiver. This probe
neither proves the entire chip clean nor validates a broad flatten-all change
for SRAMs, runtime cost, extraction, or LVS. No such production patch was made.

### The upstream SRAM independently fails full Magic DRC

The PDK's standalone, unchanged
`libs.ref/sg13g2_sram/gds/RM_IHPSG13_1P_1024x32_c2_bm_bist.gds`, with the same
six flatglob patterns supplied by upstream `read_sram_gds.tcl`, produces:

- 27 Cnt.c N-diffusion contact-enclosure markers;
- 68 SRAM-exception contact-enclosure markers;
- **95 total**, without top-level routing, PDN, pads, sealring or filler.

This independently establishes a pinned-library/Magic compatibility blocker.
It does not establish that these are fabrication defects rather than remaining
Magic import/derived-layer artifacts. The extra 13 SRAM-exception markers in
the full chip's first SRAM are not explained by this isolated probe; they must
not be silently waived or attributed to rotation without further evidence.

## Installed versus upstream expectations

`evidence/upstream-hashes.json` compares installed bytes against raw files at
the exact upstream PDK revision. All five SHA-256 pairs match: Magic DRC deck,
Magic CIF input deck, SRAM-import helper, SRAM GDS, and IO GDS. This rules out
an installer modification to those inputs.

The isolated template environment resolves Magic to
`/nix/store/7ar043dk92xygs16rwqivrzv8s467rg0-magic-vlsi-8.3.677/bin/magic`
and KLayout to
`/nix/store/cw81fji9f4zsggnpi3h42c3smyzj4iq7-klayout-0.30.12/bin/klayout`.
The template's locked nix-eda revision is
`8a8e673d5327d1ceaf039c1e647f487148c7bd85`;
its upstream `nix/magic.nix` specifies Magic 8.3.677, matching the actual
installed derivation. These are the isolated tools, not the global Docker
Magic/KLayout versions.

Upstream `.github/workflows/ci.yml` invokes `make librelane-nodrc`; the pinned
Makefile skips Magic DRC, KLayout DRC, antenna and density for that target.
Upstream CI is therefore not evidence that this example passes full signoff.

The baseline KLayout command explicitly passes `-rd no_recommended=true`.
Its TM2.bR implementation is guarded by `RECOMMENDED`, whereas Magic full DRC
runs the rule. However, enabling recommended rules is **not demonstrated to
resolve checker disagreement**: the pinned KLayout deck also produces zero
items on both minimal two-polygon PDN probes with
`-rd no_recommended=false`, while logging execution of TM2.bR. That additional
deck/tool discrepancy remains unresolved; no KLayout zero result exonerates
the measured 2-micrometre gap against the stated 5-micrometre rule.

## Exact investigation evidence

Under the evidence root above, new files in `evidence/` are:

- `analyze_drc.py`, `drc-coordinate-map.json`: programmatic total and complete
  marker-to-instance spatial map, using KLayout's Python GDS reader.
- `targeted_drc.tcl`: reusable pinned-Magic probe; takes `PROBE_GDS`,
  `PROBE_TOP`, `PROBE_FLAT` (0 retains upstream patterns; 1 adds `*`) and
  `PROBE_REPORT` environment variables. Always uses `drc(full)`.
- `sram-native.log`, `sram-native.rpt`: completed isolated SRAM run.
- `pad-native.log`, `pad-native.rpt`, `pad-flat.log`, `pad-flat.rpt`: isolated
  native/flattened pad differential.
- `pdn-original.gds`, `pdn-spacing5.gds` and corresponding `.log`, `.rpt`,
  `.klayout.log`, `.klayout.lyrdb`: extracted two-polygon red/green probes.
- `upstream-hashes.json`, `nix-magic-derivations.json`,
  `upstream-nix-magic.nix`: exact-pin comparison evidence.
- `targeted-results.json`: machine-readable completed-probe summary.

The evidence remains in ignored `tests/run/`; only this small report is a new
tracked-source candidate. Existing user changes were not altered.

## Comparison with the previous local image

A targeted rerun in previous local image `c24fed24a8e2` (currently tagged
`0.2.0`) reproduces the same four TM2.bR markers on `pdn-original.gds`
with top cell `pdn_probe` and full Magic rules. Magic is also 8.3.677;
SHA-256 values for the DRC deck, CIF input deck, SRAM GDS and IO GDS match
the new image. The report is `evidence/old-image-pdn.rpt`.
This disproves a new-image-only origin for this PDN failure, but is not a
full-chip comparison of all 2701 markers. The earlier full IHP attempt was
killed during filler generation, before completing DRC.

## Required resolution before another full flow

Keep this as a signoff blocker. Establish a geometry-preserving, selective pad
import flattening correction; resolve the SRAM contact markers against the
pinned Magic input/derived-layer semantics; and redesign the 6/2 PDN pairing
for the 5-micrometre wide-line spacing while preserving SRAM power connections.
Validate candidate changes first against these isolated probes and the existing
GDS checkpoint. Only after those pass should implementation be repeated, with
all original DRC, density, antenna, XOR, LVS and power-grid checks retained.
No pin upgrade or broad rule change is justified by this investigation.
