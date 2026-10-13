# Tool installation smoke tests

Inside the EDA container, run `bash /home/designer/tests/run_all.sh`, or run
`./run_all.sh` from the mounted tests directory. This is the only suite runner;
it does not call Docker or require the repository's `runtime/` directory.
Run `bash /home/designer/tests/analog/netgen-lvs.sh` for one test.

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
the Xyce and ORFS tests and the Xyce/MCY inventory entries. Excluded tests are
reported separately, never counted as passes. Remove the relevant entries to
re-enable them. `helpers/` contains support code, not standalone tests.

Only required fixtures are in `data/`. Generated artifacts, individual logs,
`summary.tsv`, image identity and the resolved tool inventory are under the
ignored `run/` directory. Small self-checking designs are used; only the retained
LibreLane smoke tests run complete flows. These checks are not fabrication signoff.

## Coverage

| Manifest tool | Functional check |
| --- | --- |
| ngspice | NMOS operating points using IHP, Sky130 and GF180 models |
| Xyce | Three-point resistor-divider DC sweep with numeric assertions |
| Open PDKs / IHP PDK | Environment, installed technologies/models; simulation, extraction, DRC and GF180 PCell geometry |
| Magic | GDS read and extraction of resistors/capacitors |
| OpenVAF | Compile Verilog-A resistor, load OSDI in ngspice and verify current |
| KLayout | IHP active-layer DRC report and GF180 PCell GDS |
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
| LibreLane | Built-in smoke test and GF180 counter flow with final metrics/GDS |

Trilinos is Xyce's build dependency, not a separate runtime application.
GTKWave is currently supplied by apt rather than the commented source-build
stage. The inventory records installed executable paths, not proof that all
floating apt/Python/Nix packages match a source revision.

## Confirmed installation gaps in the tested 2.0.0 image

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
UID_RUNTIME_IMAGE=isaiassh/unic-cass-tools:2.0.0 python3 -m unittest discover -s tests -p test_uid_runtime.py -v
```
