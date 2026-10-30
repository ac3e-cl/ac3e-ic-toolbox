#!/bin/bash
# Offline, repeatable adaptations of the pinned open_pdks installation.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export LIBS_TECH="${PDK_ROOT:?}/gf180mcuD/libs.tech"
export KLAYOUT_HOME="$LIBS_TECH/klayout"
python3 "$SCRIPT_DIR/fix-tech-file.py" --pdk gf180mcuD "$KLAYOUT_HOME/tech/gf180mcu.lyt"
python3 - "$LIBS_TECH" "$SCRIPT_DIR" <<'PY'
from pathlib import Path
import shutil
import sys
tech, scripts = map(Path, sys.argv[1:])
rc = tech / 'xschem/xschemrc'
text = rc.read_text().replace('append XSCHEM_LIBRARY_PATH :$env(PWD)', 'append XSCHEM_LIBRARY_PATH :$env(PDK_ROOT)/gf180mcuD/libs.tech/xschem')
text = text.replace('set 180MCU_MODELS ${PDK_ROOT}/models/ngspice', 'set 180MCU_MODELS $env(PDK_ROOT)/gf180mcuD/libs.tech/ngspice')
rc.write_text(text)
k = tech / 'klayout'
cells = k / 'pymacros/cells'
cells.mkdir(exist_ok=True)
for source in (k / 'pymacros').iterdir():
    if source.name == 'cells' or source.suffix == '.lym':
        continue
    target = cells / source.name
    if target.exists():
        raise RuntimeError(f'ambiguous PCell resource: {source}, {target}')
    # OverlayFS can reject directory rename from a lower Docker layer (EXDEV).
    # shutil.move falls back to copying with symlinks preserved, then removal.
    shutil.move(str(source), str(target))
macro = k / 'tech/gf180mcu.lym'
if macro.exists():
    shutil.move(str(macro), str(k / 'pymacros/gf180mcu.lym'))
# These generators use gdsfactory's generic geometry API with explicit GF
# layers. Its lazy default instead interprets the open_pdks PDK environment
# selector (gf180mcuD) as an importable Python module. Activate the geometry
# backend locally, without changing the user's PDK selection or Python env.
init = cells / '__init__.py'
activation = '''from gdsfactory.generic_tech import get_generic_pdk
get_generic_pdk().activate()
'''
text = init.read_text()
if activation not in text:
    text = text.replace('import pya\n', 'import pya\n\n' + activation, 1)
    if activation not in text:
        raise RuntimeError('missing GF PCell initialization anchor')
    init.write_text(text)
shutil.copyfile(scripts / 'draw_efuse.py', cells / 'draw_efuse.py')
assert (cells / 'efuse/efuse.gds').stat().st_size > 0
assert (k / 'macros/gf180mcu_options.lym').is_file(), 'missing pinned fd_pr dropdown macros'
for path in (k / 'macros').glob('*_options.yml'):
    path.write_text(path.read_text().replace('variant: C', 'variant: D'))
path = k / 'macros/gf180mcu_options.lym'
path.write_text(path.read_text().replace(';"C"', ';"D"').replace('], 2)', '], 3)'))
PY
