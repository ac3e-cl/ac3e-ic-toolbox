import os
from pathlib import Path
import sys
import pya

# PATH selects user Python 3.11, but this macro runs in the .deb's libpython3.10.
assert sys.version_info[:2] == (3, 10), sys.version
import numpy
import gdsfactory
from gdsfactory.typings import Float2, LayerSpec
pcell_site = Path('/opt/klayout-pcells/lib/python3.10/site-packages')
for module in (numpy, gdsfactory):
    assert Path(module.__file__).resolve().is_relative_to(pcell_site), module.__file__
assert not any('/opt/eda-venv' in p or 'python3.11' in p for p in sys.path), sys.path
print('KLayout embedded Python:', sys.version)
from importlib.metadata import version
print('PCell dependencies:', numpy.__version__, version('gdsfactory'))

# open_pdks' selector is not an importable gdsfactory PDK module.
assert os.environ['PDK'] == 'gf180mcuD'
assert os.environ['GF_PDK_OPTION'] == 'D'
k = Path(os.environ['PDKPATH']) / 'libs.tech/klayout'
tech = pya.Technology()
tech.load(str(k / 'tech/gf180mcu.lyt'))
assert tech.name == 'gf180mcuD'
sys.path.insert(0, str(k / 'pymacros'))
from cells import gf180mcu
gf180mcu()
lib = pya.Library.library_by_name('gf180mcu')
assert lib and lib.layout().pcell_declaration('nfet')
assert (k / 'pymacros/cells/efuse/efuse.gds').stat().st_size > 0
layout = pya.Layout()
cell = layout.create_cell('nfet', 'gf180mcu', {'l': 0.28, 'w': 1.0})
assert cell is not None and not cell.bbox().empty(), 'empty GF180 PCell'
assert os.environ['PDK'] == 'gf180mcuD', 'PCell initialization changed PDK selector'
assert os.environ['GF_PDK_OPTION'] == 'D'
assert gdsfactory.get_active_pdk().name == 'generic'
print('GF180 PCell backend:', gdsfactory.get_active_pdk().name)
out = os.environ['GF_GDS_OUTPUT']
layout.write(out)
check = pya.Layout()
check.read(out)
assert check.top_cells() and any(not c.bbox().empty() for c in check.top_cells())
print('GF180 nfet PCell GDS:', out)
