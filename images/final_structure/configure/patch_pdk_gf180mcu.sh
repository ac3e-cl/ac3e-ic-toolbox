#!/bin/bash
# Offline, repeatable adaptations; preserve Ciel's upstream geometry and decks.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export LIBS_TECH="${PDK_ROOT:?}/gf180mcuD/libs.tech"
export KLAYOUT_HOME="$LIBS_TECH/klayout"
# Only legacy open_pdks used the custom technology rewrite. Ciel ships a
# complete technology with its own connectivity, dbu and additional backends.
if [[ ! -d "$KLAYOUT_HOME/tech/pymacros/cells" ]]; then
    python3 "$SCRIPT_DIR/fix-tech-file.py" --pdk gf180mcuD "$KLAYOUT_HOME/tech/gf180mcu.lyt"
fi
python3 - "$LIBS_TECH" "$SCRIPT_DIR" <<'PY'
from pathlib import Path
import re
import shutil
import sys
tech, scripts = map(Path, sys.argv[1:])
rc = tech / 'xschem/xschemrc'
text = rc.read_text().replace('append XSCHEM_LIBRARY_PATH :$env(PWD)', 'append XSCHEM_LIBRARY_PATH :$env(PDK_ROOT)/gf180mcuD/libs.tech/xschem')
text = text.replace('set 180MCU_MODELS ${PDK_ROOT}/models/ngspice', 'set 180MCU_MODELS $env(PDK_ROOT)/gf180mcuD/libs.tech/ngspice')
rc.write_text(text)
k = tech / 'klayout'
ciel_layout = (k / 'tech/pymacros/cells').is_dir()
if ciel_layout:
    # Preserve every upstream geometry setting; only namespace the GUI
    # technology to the retained public variant (existing selection contract).
    lyt = k / 'tech/gf180mcu.lyt'
    lyt.write_text(lyt.read_text().replace('<name>gf180mcu</name>', '<name>gf180mcuD</name>'))
    # Keep upstream paths and licenses intact. Public aliases support the
    # existing launcher/tests without duplicating or relocating rule decks.
    for name in ('pymacros', 'macros', 'drc', 'lvs'):
        target = k / name
        source = k / 'tech' / name
        if not source.is_dir():
            raise RuntimeError(f'missing Ciel KLayout resource: {source}')
        if target.is_symlink() and target.resolve() == source.resolve():
            continue
        if target.exists() or target.is_symlink():
            raise RuntimeError(f'ambiguous Ciel KLayout resource: {target}')
        target.symlink_to('tech/' + name, target_is_directory=True)
else:
    # Compatibility with an already-installed legacy image, not an installer
    # fallback. Directory moves must support lower Docker layers (EXDEV).
    cells = k / 'pymacros/cells'
    cells.mkdir(exist_ok=True)
    for source in (k / 'pymacros').iterdir():
        if source.name == 'cells' or source.suffix == '.lym':
            continue
        target = cells / source.name
        if target.exists():
            raise RuntimeError(f'ambiguous PCell resource: {source}, {target}')
        shutil.move(str(source), str(target))
    macro = k / 'tech/gf180mcu.lym'
    if macro.exists():
        shutil.move(str(macro), str(k / 'pymacros/gf180mcu.lym'))
cells = k / 'pymacros/cells'
# gdsfactory 7 otherwise interprets PDK=gf180mcuD as a Python module.
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
# Both Ciel PCell backends still hard-code /home/$USER. Locate the bundled
# efuse relative to its module (also works under arbitrary runtime UID/HOME).
for backend in ('cells', 'klayout_api_cells') if ciel_layout else ('cells',):
    directory = k / 'pymacros' / backend
    assert (directory / 'efuse/efuse.gds').stat().st_size > 0
    source = directory / 'draw_efuse.py'
    if not ciel_layout:
        shutil.copyfile(scripts / 'draw_efuse.py', source)
    text = source.read_text()
    text = re.sub(r'(?m)^USER = os\.environ\["USER"\]\n', '', text)
    text = re.sub(r'(?m)^gds_path = .+$', 'gds_path = str(Path(__file__).resolve().parent / "efuse")', text)
    if 'from pathlib import Path' not in text:
        text = 'from pathlib import Path\n' + text
    source.write_text(text)
options = k / 'macros/gf180mcu_options.lym'
assert options.is_file(), 'missing pinned dropdown macros'
for path in (k / 'macros').glob('*_options.yml'):
    path.write_text(re.sub(r'(?m)^(\s*variant:\s*)[A-F](\s*)$', r'\g<1>D\2', path.read_text()))
text = options.read_text()
if ciel_layout:
    # Upstream Ruby uses %w[...] and zero-based selection indices, not the
    # old Python-like selection representation. Change only variant defaults.
    text = re.sub(r'(add_selection\("variant",[^\n]+, )\d+(\))', r'\g<1>3\2', text)
else:
    text = text.replace(';"C"', ';"D"').replace('], 2)', '], 3)')
options.write_text(text)
PY
