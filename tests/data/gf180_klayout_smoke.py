import os
from pathlib import Path
import sys
import pya
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
out = os.environ['GF_GDS_OUTPUT']
layout.write(out)
check = pya.Layout()
check.read(out)
assert check.top_cells() and any(not c.bbox().empty() for c in check.top_cells())
print('GF180 nfet PCell GDS:', out)
