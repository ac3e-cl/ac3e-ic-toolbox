# Local validation — release/0.3.1

## Candidate image

- Image: `isaiash/ac3e-ic-toolbox:0.3.1`
- ID: `sha256:c193ad93a3b2735cb50d37da0497c029765211a9a366fda54a4838e906b7e3ae`
- Size reported by Docker: `41244826951` bytes.
- Local branch: `release/0.3.1`. Validation status is independent of any subsequent
  commit/push; it does not constitute image approval or publication.
- Final build: exit 0, process `proc_90e6a37deb50`.

## Evidence obtained

- 215 host tests: OK, 2 skipped; `build/_build_logs/host-0.3.1.log`.
- Bash syntax, Docker check with the manifest and `git diff --check`: passed.
- Offline candidate startup: Ciel 3.1.0, precheck launcher with the run-tag fix
  and precheck activation installed; GF resolves to revision
  `792ef67037d74c8c51811eab3ce23cf793491296` under the Ciel root.
- Preliminary tests in the reference overlay (NOT a substitute for the candidate):
  new SCL selection, IHP/GF/IHP switching, environment, MOSFET, PCells and the full
  GF LibreLane flow pass; `build/_build_logs/gf-runtime-probe-tests.log`.
- 19 real rule-regression cases in that overlay pass, including negative controls
  and comparison with the upstream LDMOS golden reference. Evidence in
  `tests/run/gf180-rules/validation.log`. This is not manufacturing signoff.

## Integration gates (current status)

- Regular offline suite on the candidate ID: **PASS**, exit 0: 26 PASS,
  0 FAIL and 7 explicit exclusions, 33 entries total. Summary:
  `tests/run/summary.tsv`; log `build/_build_logs/release-0.3.1-regular.log`.
  Includes new Ciel, negative precheck and GF rule tests, and IHP regressions.
- Offline IHP and GF template activation with UID/GID `12345:23456`: PASS,
  writable HOME, accessible LibreLane executable and private PDK.
- Full flows: GF **PASS**, including RTL, full implementation, metrics,
  GDS and gate-level simulation. Evidence: `tests/run/librelane-template-gf/run.Gsz2E2kF/project/evidence`.
- IHP **FAIL** after completing 82 stages: Magic DRC 2701, KLayout DRC 0, LVS PASS.
  Comparison completed: the DRC report matches the baseline byte for byte;
  all 2701 markers, coordinates and duplicates are identical. The 80 inventoried
  IHP inputs and the isolated tools compared also match. No regression was
  observed in this failure. Details: `release-0.3.1-ihp-blocker.md`.
  Evidence: `tests/run/librelane-template-ihp/run.9sE0hlZI/project/evidence/flow.log`.
  The long suite exits 1: 1 PASS, 1 FAIL, 1 SKY exclusion.
  Summary: `tests/run/full/summary.tsv`; log `build/_build_logs/release-0.3.1-full.log`.
- IHP gate-level simulation run independently on that checkpoint's netlist:
  1 testcase PASS, no errors or skips, XML `evidence/gl-after-drc-failure.xml`.
  A `final` link was created only in the disposable test copy. This functional
  result does NOT change the full flow's DRC FAIL.
- Full positive precheck on the GF-generated GDS: **INTERRUPTED when work was
  closed at the user's request**, after more than three hours;
  it had reached KLayout DRC, DF.3c rules. No PASS or signoff is claimed.
  Preserved log: `build/_build_logs/release-0.3.1-precheck-positive.log`.
- Precheck container stopped and absence of validation containers for this release
  verified. Image and evidence preserved; no caches deleted.

## Closure

Work closed at the user's request. Image built and branch prepared,
but **release not approved**: IHP full reproduces a pre-existing DRC blocker and
the full positive precheck remains incomplete. No rules or exclusions were changed
to turn failures into PASS. No commit, push or publication was performed.
Changes remain in the `release/0.3.1` working tree.

Most of the time was spent on the native/Nix build, the full GF flow
(3 h 44 min 20 s), the IHP flow (1 h 11 min 20 s) and the full precheck,
interrupted after more than 3 h. Execution used one worker/thread for heavy flows
to limit memory pressure; this was not a reduced test.
