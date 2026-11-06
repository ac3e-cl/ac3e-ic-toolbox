# GF180 real rule-deck regression fixtures

Run inside the installed EDA image:

```bash
bash /home/designer/tests/pdk/gf180-rules.sh
```

Host reproduction from repository root (offline, sequential, threads=1,
workers=1; no full-chip designs):

```bash
docker run --rm --network none --entrypoint bash \
  -v "$PWD/tests:/home/designer/tests" \
  ac3e-gf-runtime-probe:0.3.1 /home/designer/tests/pdk/gf180-rules.sh
python3 -B -m unittest discover -s tests -p test_gf_rules.py -v
```

The shell test is automatically discovered by `tests/run_all.sh`. It needs
Python `klayout.db` and the global Ruby-enabled `klayout` executable, not pytest
or extra packages. The PDK-only build stage is not assumed to contain those.
Every invocation creates its own `tests/run/gf180-rules/run.*` directory, with
GDS, logs, real `.lyrdb` reports, `results.json`, and `provenance.json`. A report
must contain the asserted category even when its expected count is zero.
KLayout returns zero for DRC violations, so exit status alone is not an oracle.

## Synthetic red/green cases

The helper generates tiny layouts in 1 nm DBU; no binary inputs are vendored.

- DCF.1a: 30 um empty COMP gap -> 1 marker; identical gap filled with
  Dummy COMP (22/4) -> 0; NDMY (111/5) exception -> 0; 19 um gap -> 0.
  Extent is held fixed with border 63/0.
- DF.11: butted NCOMP/PCOMP shared edge 299 nm -> 1; 300/301 nm -> 0.
- CO.5a and CO.5b independently: contact implant enclosure 70 nm -> 1;
  exactly 100 nm -> 0, with the opposite rule remaining zero. Removing the
  opposite implant makes the original deficient contact non-butted -> 0.
- Each violating report is also checked against an intentionally wrong clean
  expectation, which must fail (`RED-CONTROL`, saved in `negative_controls`).

Only the named target categories are asserted for these minimal layouts. Other
rule violations are expected and all category counts are retained in JSON.

## Installed upstream fixtures and licenses

Reuse `comp`, `contact`, `ldnmos`, and `ldpmos` GDS and golden `.lyrdb` files
in `/opt/pdks/gf180mcuD/libs.tech/klayout/tech/drc/testing/unit` directly from
the image. The installed upstream README documents golden geometry comparison.
These tests compare **all category counts and sorted marker geometry by
cell/rule**, not merely presence of an output. No upstream files or license
headers are removed, rewritten, or copied into this repository. The upstream
framework/decks carry GlobalFoundries PDK Authors Apache-2.0 notices; the image
retains the upstream licensing context. Golden files are trusted pinned
upstream expectations, not regenerated from the result under test.

Two small filler cells (`fill_1`, `fill_64`) are extracted at runtime from the
installed `gf180mcu_fd_sc_mcu7t5v0` GDS into ignored outputs only, retaining the
source library untouched. Each must have zero DCF.1a, DF.11, CO.5a and CO.5b
markers. No third-party layout is redistributed as committed test data.

## Scope and limitations

This is regression coverage, **not fabrication signoff**. It does not assert
all-rule cleanliness of fillers or minimal synthetic layouts. It does not
validate placed filler rows, abutment/orientations, fillcap/filltie, all standard
cell libraries, complete LDMOS devices by independent analytic expectations,
LVS, full-chip density, every DCF keepout, or DF.11's upstream-noted 90-degree
combined-edge limitation. LDMOS coverage is exact comparison to the installed
upstream mixed passing/violating fixtures. Tests run variant D, flat mode only;
other variants and deep/tiling/parallel modes are not exercised.

Hashes of input layouts, upstream golden reports, the entrypoint and Ruby deck
files, along with actual KLayout version/commands, accompany each passing run.
The probe image is a runtime validation aid, not proof that a concurrently
building final image includes the same files. Re-run on the completed release
image before making final-image claims.
