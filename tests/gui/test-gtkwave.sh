#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$here/../common.sh"
load_design_env
for cmd in gtkwave vcd2fst fst2vcd python3 timeout; do require_command "$cmd"; done
run="$here/../run/gtkwave"
mkdir -p "$run"
run=$(cd "$run" && pwd)
rm -f "$run/pulse.fst" "$run/roundtrip.vcd"
source "$here/../helpers/gui-display.sh"
start_gui_display
vcd2fst "$here/../data/gui/pulse.vcd" "$run/pulse.fst" >"$run/conversion.log" 2>&1
fst2vcd "$run/pulse.fst" --output="$run/roundtrip.vcd" >>"$run/conversion.log" 2>&1
python3 - "$run/roundtrip.vcd" <<'PY'
import pathlib, re, sys
text = pathlib.Path(sys.argv[1]).read_text()
match = re.search(r'\$var\s+wire\s+1\s+(\S+)\s+clk\s+\$end', text)
assert match, 'clk signal missing after FST round trip'
signal = match[1]
time = None
transitions = []
for line in text.splitlines():
    line = line.strip()
    if line.startswith('#'):
        time = int(line[1:])
    elif re.fullmatch('[01]' + re.escape(signal), line):
        transitions.append((time, int(line[0])))
assert transitions == [(0,0),(5,1),(10,0),(15,1),(20,0)], transitions
assert re.search(r'\$timescale\s+1ns\s+\$end', text), 'timescale changed'
print('Verified clk: 5 transitions, 0..20 ns, levels 0/1')
PY
# --exit is a documented loader benchmark: success requires a normal exit,
# not a killed GUI. Exercise the actual GTKWave binary on the generated FST.
if ! timeout 15s gtkwave --exit "$run/pulse.fst" >"$run/load.log" 2>&1; then
    cat "$run/load.log" >&2
    fail 'GTKWave FST load failed or exceeded deadline'
fi
pass 'GTKWave: exact VCD/FST round trip and GUI-backed FST load'
