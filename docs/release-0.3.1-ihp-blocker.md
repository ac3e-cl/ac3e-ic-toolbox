# Release 0.3.1: IHP full-flow blocker, no observed GF180 regression

## Result

**IHP full remains BLOCKED; no complete validated fix exists within the
permitted scope.** The full flow was not repeated, and production code, PDK,
pins, locks and PASS criteria were not modified. No checks are proposed for omission.
KLayout DRC 0, LVS PASS and RTL PASS do not constitute signoff. The runner did not
run GL after the flow failed; it was subsequently run independently on that
checkpoint's netlist and passed 1 testcase, without skips or errors
(`evidence/gl-after-drc-failure.xml`). That result does not change the physical FAIL.

- Candidate: `sha256:c193ad93a3b2735cb50d37da0497c029765211a9a366fda54a4838e906b7e3ae`.
- Baseline: `sha256:ea126a1a4c4a209134aad8bf90a21a4074201f20682c87a677f065f773e3c811`.
- New: `tests/run/librelane-template-ihp/run.9sE0hlZI/project/`.
- Baseline: `tests/run/librelane-template-ihp/run.9FsoK7JP/project/`.
- Previous context: [ihp-template-drc-investigation.md](ihp-template-drc-investigation.md).

## Exact comparison, not just totals

Both `librelane/runs/template/67-magic-drc/reports/drc.magic.rpt` files were
parsed with Python `Decimal` and `Counter`, comparing multisets of
**(literal category, four coordinates)** while retaining duplicates.

| Magic category | Baseline | Candidate | Delta |
| --- | ---: | ---: | ---: |
| TM2.bR, wide/long metal | 624 | 624 | 0 |
| Partial overlap/abutment between subcells | 1792 | 1792 | 0 |
| Cnt.c N-diffusion contact enclosure | 54 | 54 | 0 |
| Can't overlap those layers | 82 | 82 | 0 |
| Cnt.c SRAM exception | 149 | 149 | 0 |
| **Total** | **2701** | **2701** | **0** |

**Zero markers added or removed; identical coordinates and multiplicities.**
Even the complete reports are byte-for-byte identical: SHA-256
`575f88b9d49a0d7f9ddf810c9b4000c0047918031d2ba3613d66b8b0398ec371`.
Final DRC/LVS metrics match; both have KLayout DRC 0 and
`design__lvs_error__count = 0`. The new `evidence/flow.log` records 2701 at
lines 8646, 10172 and 11328; the last is the final deferred error.
`evidence/rtl.xml` contains `test_counter` without failure.

## IHP inputs and effective tools

Offline inventory of **both images by ID**, not the working tree:

- All 80 inventoried files (files under `libs.tech/magic`, two SRAM/IO GDS files
  and `*.drc` decks under `libs.tech/klayout`) have matching hashes.
- The five inputs previously compared against upstream—Magic DRC deck, CIF input,
  `read_sram_gds.tcl`, SRAM GDS and IO GDS—retain the same installed and upstream
  hashes in the candidate as in the baseline. This investigation reuses
  `upstream-hashes.json`; it does not download upstream again.
- Identical IHP manifest: template `23c62045bb212175c20d8186a7ab308e15fba98c`,
  isolated PDK `7bbb4b5a5b64c446fedc64eacadc33fa65ade276`, LibreLane
  `c5b5099e55f4e3bed507f2e79441ecfd6432d65c`.
- `evidence/flake.lock`, recorded executables, LibreLane version and
  `librelane/config.yaml` are identical. `67-magic-drc/config.json` differs only
  in run-identifier paths; after normalization they match.
- Six resolved tools (Magic, KLayout, LibreLane, OpenROAD, Yosys and Python)
  have identical Nix paths and executable/wrapper SHA-256 hashes.
  The inventoried Magic/KLayout `.drv` files are also identical.

Template signoff tools, **not** global Docker versions:

```text
/nix/store/7ar043dk92xygs16rwqivrzv8s467rg0-magic-vlsi-8.3.677/bin/magic
/nix/store/cw81fji9f4zsggnpi3h42c3smyzj4iq7-klayout-0.30.12/bin/klayout
/nix/store/zkadb62gnclvlbdnz0q97agj9qv9jrc2-magic-vlsi-8.3.677.drv
/nix/store/6avas7ibvbjp4lwr67djxdqbgv6n86i3-klayout-0.30.12.drv
```

SHA-256 of the active Magic `.drv`:
`3efa0d9eeca7b7ad48c4ce41aa96a336aa03076d561333ffe611b471e0e8b1f7`;
active KLayout:
`0cbd4c08abb373f8655a4e7beff51a54d185e06ae99b27fd6dd4121f879aca92`.
Preserved `.drv` text identifies their outputs. `nix-store --query
--deriver` could not open the database lock with a read-only rootfs;
the `.drv` files were compared directly without making Nix writable. The first
attempt also found no global `nix-store` alias; the installed binary was located
under `/nix/store/*-nix-*/bin/nix-store`.

**Limited conclusion:** this IHP failure exactly reproduces the previous blocker;
it is not an observed regression caused by the GF180 update.
This does not certify the whole image or all uninventoried IHP inputs.
The relevant PDK is isolated under `/opt/librelane-templates/pdks/ihp`,
not the global PDK identified by `IHP_PDK_REPO_COMMIT` in the Docker environment.

## Miniprobes repeated in the candidate

The baseline's `targeted_drc.tcl` was reused, always with `drc style drc(full)`;
no deck was edited. Runs were sequential, offline, with a read-only rootfs,
one CPU, a hard 384 MiB RAM limit without swap and a 55 s timeout per probe.
The positive GF precheck was active at the start and was not stopped or modified.

| Existing probe | Magic result | Time including Docker startup |
| --- | --- | ---: |
| `pdn-original.gds`, 2 µm gap | 4 TM2.bR | 1.235 s |
| `pdn-spacing5.gds`, 5 µm gap | 0 | 0.987 s |
| IO `sg13g2_IOPadOut30mA`, upstream flatglob | 112 abutment + 2 overlap | 34.134 s |
| Same IO, adding `gds flatglob *` | 0 | 3.439 s |

All four reports are byte-for-byte identical to their baseline miniprobes.
Magic exit 0 was not treated as PASS: `PROBE_COUNT` was required and reports
were read. Zero errors apply only to those probes.

### Defensible minimal fix and scope limit

1. **PDN:** the tested local geometry change increases the gap from 2 to 5 µm
   for the probe's two 6 µm polygons. The TM2.bR rule is unchanged. This does not
   validate changing `PDN_HSPACING` globally: SRAM power connections and coverage
   of all checkpoint markers are missing.
2. **Pads:** import flattening removes the isolated pad's 114 errors without
   changing its GDS or rules. This is a direction for a fix, not a validated
   integration patch: `flatglob *` over all IO does not demonstrate safe selective
   chip flattening or extraction/LVS equivalence.
3. **SRAM:** the independent baseline probe remains evidence of 95 errors
   (27 Cnt.c + 68 SRAM exception) with the same inputs and tool. It was not
   repeated because another potentially heavy job was unnecessary. There is no
   validated import/derived-layer fix. The first in-chip SRAM's 13 extra markers
   still lack a demonstrated explanation.

Therefore **no complete, authorized and validated minimal change makes
IHP full PASS**. Resolution requires specific PDN/import/SRAM integration work
and subsequent physical validation, outside this read-only investigation.
It is not defensible to turn positive LVS/KLayout/RTL results into a flow PASS,
relax rules, change pins or exclude Magic.

## Evidence and exact reproduction

New ignored evidence under the new run's `evidence/`:

- `compare_release_031.py`, `release-031-comparison.json`: literal categories,
  complete marker comparison, hashes and metrics.
- `inventory_ihp.py`, `{baseline,candidate}-inventory.json`,
  `release-031-inventory-comparison.json`: SHA-256, `.drv` text, resolved paths
  and comparison with the baseline's five exact upstream URLs.
- `run_miniprobes.py`, `release-031-miniprobes.json`: complete Docker commands,
  flags, variables, timings, exit codes, counts and report hashes.
- `release-031-{pdn-original,pdn-spacing5,pad-native,pad-flat}.{log,rpt}`.

From the repository root:

```bash
E=tests/run/librelane-template-ihp/run.9sE0hlZI/project/evidence
python3 "$E/compare_release_031.py"
# Inventory: both IDs above, same invocation, read-only evidence mount:
docker run --rm --network none --memory 256m --cpus 1 --read-only \
  -v "$PWD/$E:/evidence:ro" --entrypoint /usr/bin/python3 IMAGE_ID \
  /evidence/inventory_ihp.py
# Only the four bounded probes described above, never the full flow:
python3 "$E/run_miniprobes.py"
```

Sources: reports/config/metrics/XML from both runs; bytes from both immutable
images; baseline `upstream-hashes.json`, `nix-magic-derivations.json`,
`targeted-results.json`, `sram-native.rpt`; previous investigation report.
No commits. Only new document: this one; all other writes are ignored evidence.
Concurrent repository changes were not altered.
