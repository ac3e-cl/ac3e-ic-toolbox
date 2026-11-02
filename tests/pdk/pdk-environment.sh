#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(dirname "$SCRIPT_DIR")"
source "$TEST_ROOT/common.sh"
load_design_env
require_command klayout
for selected in ihp-sg13g2 gf180mcuD; do
    sak-pdk "$selected"
    test "$PDKPATH" = "$PDK_ROOT/$PDK"
    test -d "$PDKPATH/libs.ref/$STD_CELL_LIBRARY"
    test -s "$PDKPATH/libs.tech/xschem/xschemrc"
    test -s "$PDKPATH/libs.tech/magic/$PDK.magicrc"
    if [[ "$selected" == gf180mcuD ]]; then
        test "${GF_PDK_OPTION:-}" = D
        test -s "$PDKPATH/libs.tech/ngspice/sm141064.ngspice"
    else
        test -z "${GF_PDK_OPTION:-}"
    fi
    python3 - <<'PY'
import os
from pathlib import Path
import xml.etree.ElementTree as ET
p = Path(os.environ['PDKPATH']) / 'libs.tech'
assert any(x.stat().st_size for x in (p / 'ngspice').rglob('*') if x.is_file()), 'no models'
files = list((p / 'klayout').rglob('*.lyt'))
assert files, 'no KLayout technology'
for file in files:
    ET.parse(file)
PY
    klayout -b -r "$TEST_ROOT/data/gf180_environment_tech.py"
    pass "$selected environment and technology resources"
done
