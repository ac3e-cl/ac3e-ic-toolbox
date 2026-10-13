#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$here/../common.sh"
load_design_env
for cmd in gaw python3 timeout xwininfo; do require_command "$cmd"; done
run="$here/../run/gaw3-xschem"
mkdir -p "$run"
run=$(cd "$run" && pwd)
rm -f "$run/render.png" "$run/export.dat"
source "$here/../helpers/gui-display.sh"
start_gui_display
mkdir -p "$run/config"
gaw -p 1946 -C "$run/config" >"$run/gaw.log" 2>&1 &
gui_pids+=("$!")
# Talk-to-Gaw commands are acknowledged by a blank line; any error fails.
# Bound both startup and individual command response times, then compare the
# exported *displayed* trace to the input and decode the actual rendered PNG.
timeout 20s python3 "$here/verify-gaw.py" "$here/../data/gui/pulse.dat" "$run" >"$run/verification.log" 2>&1 || {
    cat "$run/verification.log" "$run/gaw.log" >&2
    fail 'gaw waveform load/render verification failed or exceeded deadline'
}
kill -0 "${gui_pids[1]}" || fail 'gaw exited unexpectedly'
xwininfo -root -tree >"$run/windows.log"
grep -qi gaw "$run/windows.log" || fail 'gaw GUI window missing'
cat "$run/verification.log"
pass 'gaw3-xschem: GUI alive, waveform loaded/plotted/exported, PNG decoded'
