"""Load each selected PDK's installed technology through KLayout itself."""
import os
from pathlib import Path
import pya
files = list((Path(os.environ['PDKPATH']) / 'libs.tech/klayout').rglob('*.lyt'))
assert files, 'no KLayout technology'
for file in files:
    technology = pya.Technology()
    technology.load(str(file))
    assert technology.name, f'unnamed technology: {file}'
    print('Loaded technology:', technology.name)
