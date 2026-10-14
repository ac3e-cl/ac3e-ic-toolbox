# Digital functional smoke tests

Run from the repository root against the installed image; no build or downloads
are required:

```bash
for tool in yosys eqy sby iverilog verilator openroad orfs; do
  docker run --rm \
    --mount "type=bind,src=$PWD/tests,dst=/home/designer/tests" \
    isaiash/ac3e-ic-toolbox:0.1.0 \
    bash "/home/designer/tests/digital/test-$tool.sh"
done
```

Each strict-Bash script sources `../common.sh`, loads the image environment, and
writes evidence beneath `tests/run/digital-<tool>/`. Fixtures live in
`tests/data/digital/`.

| Test | Functional acceptance criterion |
| --- | --- |
| Yosys | Synthesize a four-bit adder, run `check -assert`, inspect nonempty JSON cells and emitted Verilog. |
| EQY | Prove arithmetic addition equivalent to an independently implemented ripple-carry adder using SAT; require the EQY `PASS` marker. |
| SBY | Prove three arithmetic invariants for all adder inputs with ABC PDR; require `PASS` in the SBY status file. |
| Icarus Verilog | Compile and simulate a self-checking testbench over all 256 input pairs, including carry overflow. |
| Verilator | Generate C++, compile/link a real executable, and simulate the same 256 input pairs with a self-checking C++ driver. |
| OpenROAD | Load Nangate45 LEF/Liberty, link one buffer with two nets, write ODB/DEF, and verify ODB contents in a second OpenROAD process. |
| ORFS | Run the installed flow's actual `make synth` on the adder with Nangate45; require a nonempty standard-cell mapped `1_synth.v`. Every invocation uses a fresh work directory. |

## Verified image results and gaps

Historical baseline image (release 2.0.0, not a validation of the current
`isaiash/ac3e-ic-toolbox:0.1.0` image), ID
`sha256:f1e8657a540f2a9978c2ca4eb0ebf30bcd0d8e8b861906a97beba0cb408b2368`:

- Yosys, EQY, SBY, Icarus, Verilator, and OpenROAD tests pass.
- Yosys emits `YOSYS_SYNTH_PASS cells=20`; both simulators emit
  `SIMULATION_PASS vectors=256`; OpenROAD emits
  `OPENROAD_DATABASE_PASS instances=1 nets=2`.
- Negative-control subtraction is rejected by Icarus (exit 1) and EQY (exit 2).
  ABC PDR also returns FAIL for the negative formal control, but SBY's default
  counterexample conversion then errors because `yices-smt2` is absent (exit 16).
  The passing ABC proof does not require an external SMT solver. SMT-engine and
  counterexample-conversion coverage remain gaps.
- ORFS does **not** pass in this image. Its startup hook prints `PDK set to ...`
  into child-shell stdout, corrupting make `$(shell ...)` values and yielding
  `No rule to make target 'set'`. The ORFS test disables only repeated child-shell
  `BASH_ENV` loading after the environment has already been loaded. This exposes
  the next blocker: ORFS revision
  `40674dd5cf48db6dc9028d6ab5a98f107208f5bb` uses `read_liberty -unit_delay`
  and `-ignore_buses`, unsupported by installed Yosys 0.44. Direct reproduction:

  ```bash
  yosys -p 'read_liberty -overwrite -setattr liberty_cell -unit_delay -wb -ignore_miss_func -ignore_buses /opt/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
  ```

  This fails with `Command syntax error: Unknown option or option in arguments`
  at `-unit_delay`. The actual `make synth` exits 2 during canonicalization;
  the retained ORFS test intentionally reports the integration failure rather
  than substituting a standalone Yosys synthesis. No image/installer changes
  were made.
- MCY is not installed (`command -v mcy` exits 1); its installer block is
  disabled. No installation or claimed MCY coverage is included.

These are small functional smoke tests, not place-and-route, STA timing closure,
or production signoff tests. OpenROAD checks database functionality, not STA.
