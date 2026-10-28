# Tool installation smoke tests

Inside the EDA container, run `bash /home/designer/tests/run_all.sh`, or run
`./run_all.sh` from the mounted tests directory. This is the only suite runner;
it does not call Docker or require the repository's `runtime/` directory.
Run `bash /home/designer/tests/analog/netgen-lvs.sh` for one test.

The complete GF and IHP template flows are long-running and excluded from
the habitual suite. Opt in to only these long tests with:

```bash
bash /home/designer/tests/test_all_full.sh
```

The shared runner preserves timeouts and continues after failures. Long-suite
logs and summary go to `run/full/`, separately from the habitual `run/` reports.
`exclusions.json` lists this selection under `long_running`; hard exclusions
under `tests` remain respected even in the long suite. Each template retains a
14400-second deadline, overridable with `TEST_TIMEOUT`.

Only `tests/` needs to mount at `/home/designer/tests` for the suite.
The inventory check lists expected commands/resources directly; `manifest.json`
is host build configuration and is not copied or mounted into the container.
The initially empty `shared/` is reserved for user designs. Neither test inputs
nor outputs go there.
Optional host convenience command: `make test`. The host launcher starts a
temporary container and invokes the same `run_all.sh` directly.

The runner discovers shell tests in the five category directories, continues
after failures, enforces a per-test deadline (`TEST_TIMEOUT`, default 900 seconds),
and prints the final per-test summary. Missing programs and timeouts fail unless
explicitly excluded. `exclusions.json` records user-authorized exclusions for
the Xyce and ORFS tests, the temporarily disabled SKY tests, the expensive GF/IHP template flows, and the
Xyce/MCY inventory entries. Run
`bash /home/designer/tests/pdk/librelane-template-gf.sh` manually for the complete
GF180 template flow, including IR drop, RTL/gate-level simulation and GDS checks.
Excluded tests are
reported separately, never counted as passes. Remove the relevant entries to
re-enable them. `helpers/` contains support code, not standalone tests.

Only required fixtures are in `data/`. Generated artifacts, individual logs,
`summary.tsv`, image identity and the resolved tool inventory are under the
ignored `run/` directory. Small self-checking designs are used; only the retained
LibreLane smoke tests run complete flows. These checks are not fabrication signoff.

## CVC input line endings

CVC 1.1.5 requires LF line endings in its configuration: a CR from CRLF can
become part of input and report filenames, even while CVC exits successfully.
The repository enforces LF for all four CVC fixtures through `.gitattributes`,
including checkouts with `core.autocrlf=true`. The electrical test rejects a
CRLF configuration explicitly rather than silently modifying its inputs.

Existing Windows/WSL checkouts may still contain CRLF files after updating.
Convert `tests/data/analog/cvc.cvcrc`, `cvc-inverter.cdl`, `cvc-models` and
`cvc-power` to LF using an editor's line-ending setting, preserving any local
edits. Check with `git ls-files --eol tests/data/analog/cvc*`; each working-tree
entry should show `w/lf`. No global Git configuration change is required.

## Coverage

| Manifest tool | Functional check |
| --- | --- |
| ngspice | NMOS operating points using IHP and GF180 models |
| Xyce | Three-point resistor-divider DC sweep with numeric assertions |
| Open PDKs / IHP PDK | Environment, installed technologies/models; simulation, extraction, DRC and GF180 PCell geometry |
| Magic | GDS read and extraction of resistors/capacitors |
| OpenVAF | Compile Verilog-A resistor, load OSDI in ngspice and verify current |
| KLayout | IHP active-layer DRC report; embedded Python 3.10 and isolated numpy/gdsfactory imports; GF180 PCell GDS |
| Xschem | Netlist a connected resistor schematic |
| Netgen | Accept matching netlists and reject a topology mismatch |
| gaw3-xschem | Load, plot, export numeric waveform and decode rendered PNG |
| Yosys | Synthesize a four-bit adder and validate mapped netlist |
| EQY | Prove arithmetic and ripple-adder implementations equivalent |
| SBY | Prove arithmetic assertions using ABC PDR |
| MCY | Installation inventory gate; functional test blocked because installation is disabled |
| CVC | Complete voltage-aware checks on a two-transistor inverter |
| Verilator | Compile and run all adder input combinations |
| Icarus Verilog | Run all adder input combinations |
| GTKWave | Exact VCD/FST round trip and actual GUI-backed FST loading |
| OpenROAD | Create database, write DEF/ODB and validate ODB round trip |
| ORFS | Actual Nangate45 synthesis target with mapped-netlist assertions |
| Nix | Offline expression evaluation with result assertion |
| LibreLane | Explicit GF180 counter flow with final metrics/GDS; opt-in complete IHP/GF template flows |

Trilinos is Xyce's build dependency, not a separate runtime application.
SKY130 simulation, Tiny Tapeout SKY integration scripts, fixtures and helper code
are preserved. SKY is temporarily excluded from the image for space analysis,
with reintroduction planned for a later release. The three SKY-dependent shell
tests (`ngspice-sky130-mosfet.sh`, `librelane-template-sky.sh` and
`librelane-smoke.sh`, which defaults to SKY130) are hard-excluded in
`exclusions.json`: both regular and full suites report them as `EXCLUDED`, never
as passes. The adapter's host tests in `images/librelane/sky/test_bootstrap.py`
are retained with an explicit `unittest.skip` while its installer is absent.
`pdk/librelane-gf180-smoke.sh` retains a complete
small counter flow using explicit GF180 settings and final-output assertions.
The no-SKY image still requires a build and container integration validation;
host contract tests are not runtime EDA evidence.
GTKWave is currently supplied by apt rather than the commented source-build
stage. The inventory records installed executable paths, not proof that all
floating apt/Python/Nix packages match a source revision.

## Historical installation gaps in the tested 2.0.0 baseline

These results describe the historical baseline, not verification of the current
`isaiash/ac3e-ic-toolbox:0.1.0` image. Rebuild and rerun the suite to validate it.

- Xyce has a builder stage but is not copied to the final image.
- MCY is listed in the manifest but its installation block is commented out.
- The pinned ORFS uses `read_liberty -unit_delay -ignore_buses`, unsupported by
  the installed Yosys 0.44. When enabled, the ORFS test fails instead of
  substituting a hand-written flow or removing the unsupported options.

Fixing these requires installation/compatibility changes and rebuilding the
image. The user chose to exclude these checks without changing installations;
the suite keeps the exclusions visible in its summary. MCY has no functional
test until installation is enabled; its absence is recorded, not validated.

Host repository contracts run separately:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
UID_RUNTIME_IMAGE=isaiash/ac3e-ic-toolbox:0.1.0 python3 -m unittest discover -s tests -p test_uid_runtime.py -v
```
