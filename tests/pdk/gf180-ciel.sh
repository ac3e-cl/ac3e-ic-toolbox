#!/usr/bin/env bash
# Verify the installed GF revision, public Ciel and PDK switching offline.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(dirname "$SCRIPT_DIR")"
source "$TEST_ROOT/common.sh"
load_design_env
require_command ciel
python3 - <<'PY'
from importlib.metadata import version
assert version('ciel') == '3.1.0', version('ciel')
PY
sak-pdk ihp-sg13g2
original_ihp=$(readlink -f "$PDKPATH")
sak-pdk gf180mcuD
expected=792ef67037d74c8c51811eab3ce23cf793491296
test "${GF180_PDK_COMMIT:?missing installed GF revision}" = "$expected"
resolved=$(readlink -f "$PDKPATH")
[[ "$resolved" == "$PDK_ROOT/ciel/gf180mcu/versions/$expected/gf180mcuD" ]]
for library in gf180mcu_fd_sc_mcu7t5v0 gf180mcu_as_sc_mcu7t3v3 gf180mcu_ocd_sc_rt12t3v3; do
    sak-pdk gf180mcuD "$library"
    test "$STD_CELL_LIBRARY" = "$library"
    test -d "$PDKPATH/libs.ref/$library"
done
python3 - <<'PY'
import os
from pathlib import Path
root = Path(os.environ['PDKPATH'])
broken = [str(p) for p in root.rglob('*') if p.is_symlink() and not p.exists()]
assert not broken, broken
PY
sak-pdk ihp-sg13g2
test "$(readlink -f "$PDKPATH")" = "$original_ihp"
test -z "${GF_PDK_OPTION+x}"
pass 'Ciel 3.1.0, wafer GF revision, new SCL options and IHP/GF/IHP switching'
