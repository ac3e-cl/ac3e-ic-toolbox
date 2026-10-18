#!/usr/bin/env bash
# Executed inside the template-specific Nix shell, in a fresh template copy.
set -euo pipefail
key=${1:?template key required}
test_root=${2:?test root required}
jobs=${3:-2}
[[ "$jobs" =~ ^[1-9][0-9]*$ ]] || { echo 'Jobs must be a positive integer' >&2; exit 2; }
# --jobs bounds the Python executor, not OpenROAD/STA subprocess thread counts.
export _OPENLANE_MAX_CORES="$jobs" OMP_NUM_THREADS="$jobs"
mkdir -p evidence
librelane --version > evidence/librelane-version.txt
command -v librelane yosys openroad python3 > evidence/executables.txt
cp "$LIBRELANE_TEMPLATE_LOCK" evidence/flake.lock
# Keep RTL and gate-level reports separate; cocotb otherwise overwrites results.xml.
case "$key" in
    ihp|gf)
        make sim > evidence/rtl.log 2>&1
        cp cocotb/sim_build/results.xml evidence/rtl.xml
        if [[ "$key" == ihp ]]; then
            librelane librelane/config.yaml --pdk "$PDK" --pdk-root "$PDK_ROOT" \
                --manual-pdk --save-views-to final --jobs "$jobs" --run-tag template \
                > evidence/flow.log 2>&1
        else
            make defines > evidence/defines.log 2>&1
            # Pass dictionary overrides as configuration data, not CLI strings:
            # the upstream string preprocessor interprets JSON braces as format fields.
            python3 - "$jobs" > evidence/resources.json <<'PY'
import json, sys
workers = int(sys.argv[1])
print(json.dumps({
    'KLAYOUT_DRC_OPTIONS': {'decks': 'all,-antenna,-density,-cup', 'variant': 'gf180mcuD', 'workers': workers},
    'KLAYOUT_DENSITY_OPTIONS': {'decks': 'density', 'variant': 'gf180mcuD', 'workers': workers},
    'KLAYOUT_ANTENNA_OPTIONS': {'decks': 'antenna', 'variant': 'gf180mcuD', 'workers': workers},
}))
PY
            SRAM_DEFINE=SRAM_gf180mcu_fd_ip_sram librelane \
                librelane/slots/slot_1x1.yaml librelane/macros/macros_5v.yaml librelane/config.yaml evidence/resources.json \
                --design-dir "$PWD/librelane" \
                --pdk "$PDK" --pdk-root "$PDK_ROOT" --manual-pdk \
                --scl gf180mcu_fd_sc_mcu7t5v0 --pad gf180mcu_fd_io \
                --save-views-to final --jobs "$jobs" --run-tag template \
                > evidence/flow.log 2>&1
        fi
        make sim-gl > evidence/gl.log 2>&1
        cp cocotb/sim_build/results.xml evidence/gl.xml
        python3 "$test_root/helpers/verify_librelane_template.py" \
            librelane/runs/template/final evidence/rtl.xml evidence/gl.xml > evidence/result.json
        ;;
    sky)
        python -m pip check > evidence/python-dependencies.log
        # The upstream submission metadata is intentionally blank. Populate only
        # the disposable test copy, not the installed template or user designs.
        python - <<'PY'
from pathlib import Path
import yaml
path = Path('info.yaml')
data = yaml.safe_load(path.read_text())
for key, value in {
    'title': 'LibreLane integration fixture',
    'author': 'AC3E integration test',
    'description': 'Unmodified upstream RTL used for runtime validation',
}.items():
    if not data['project'].get(key):
        data['project'][key] = value
path.write_text(yaml.safe_dump(data, sort_keys=False))
PY
        (cd test; make clean; make; python -m cocotb_tools.check_results results.xml) > evidence/rtl.log 2>&1
        cp test/results.xml evidence/rtl.xml
        python tt/tt_tool.py --create-user-config > evidence/config.log 2>&1
        python tt/tt_tool.py --harden --no-docker > evidence/flow.log 2>&1
        python tt/tt_tool.py --create-tt-submission > evidence/submission.log 2>&1
        top=$(python tt/tt_tool.py --print-top-module)
        cp "tt_submission/$top.v" test/gate_level_netlist.v
        # Gate-level simulation must use the versioned root resolved by the flow.
        export PDK_ROOT
        PDK_ROOT=$(python -c 'import json; print(json.load(open("runs/wokwi/resolved.json"))["PDK_ROOT"])')
        (cd test; make clean; rm -f results.xml; make GATES=yes; python -m cocotb_tools.check_results results.xml) > evidence/gl.log 2>&1
        cp test/results.xml evidence/gl.xml
        python "$test_root/helpers/verify_librelane_template.py" \
            runs/wokwi/final evidence/rtl.xml evidence/gl.xml > evidence/result.json
        ;;
    *) echo "Unsupported template: $key" >&2; exit 2 ;;
esac
cat evidence/result.json
