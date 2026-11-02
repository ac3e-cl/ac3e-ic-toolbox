#!/usr/bin/env bash
# Check the suite's expected tools without requiring a mounted build manifest.
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"
load_design_env
mkdir -p "$TEST_ROOT/run/inventory"
python3 - "$TEST_ROOT" <<'PY'
import json
import os
from pathlib import Path
import shutil
import sys

root = Path(sys.argv[1])

exclusion_file = root / 'exclusions.json'
exclusions = json.loads(exclusion_file.read_text()).get('manifest', {}) if exclusion_file.is_file() else {}
commands = {
    'GNUCAP_NAME': 'gnucap',
    'NGSPICE_NAME': 'ngspice', 'XYCE_NAME': 'Xyce', 'MAGIC_NAME': 'magic',
    'OPENVAF_NAME': 'openvaf', 'KLAYOUT_NAME': 'klayout', 'XSCHEM_NAME': 'xschem',
    'NETGEN_NAME': 'netgen', 'GAW3_XSCHEM_NAME': 'gaw', 'YOSYS_NAME': 'yosys',
    'YOSYS_EQY_NAME': 'eqy', 'YOSYS_SBY_NAME': 'sby', 'YOSYS_MCY_NAME': 'mcy',
    'CVC_RV_NAME': 'cvc_rv', 'VERILATOR_NAME': 'verilator', 'IVERILOG_NAME': 'iverilog',
    'GTKWAVE_NAME': 'gtkwave', 'OPENROAD_NAME': 'openroad',
    'LIBRELANE_REPO_URL': 'librelane', 'NIX_INSTALLER_URL': 'nix',
}
resources = {
    'OPEN_PDKS_NAME': ('open_pdks', Path(os.environ['PDK_ROOT']) / 'gf180mcuD/libs.tech/ngspice/sm141064.ngspice'),
    'IHP_PDK_NAME': ('ihp-sg13g2', Path(os.environ['PDK_ROOT']) / 'ihp-sg13g2/libs.tech/ngspice/models/cornerMOSlv.lib'),
    'ORFS_NAME': ('OpenROAD-flow-scripts', Path(os.environ['ORFS_DIR']) / 'flow/Makefile'),
}
records = []
errors = []
for key in sorted(commands.keys() | resources.keys()):
    if key in commands:
        name = commands[key]
        path = shutil.which(commands[key])
    else:
        name, resource = resources[key]
        path = str(resource) if resource.is_file() else None
    records.append({'key': key, 'name': name, 'path': path,
                    'excluded': exclusions.get(key)})
    if not path and key not in exclusions:
        errors.append(f'Missing expected tool/resource: {key} ({name})')
(root / 'run/inventory/tools.json').write_text(json.dumps(records, indent=2) + '\n')
for record in records:
    print(f"{record['name']}: {'EXCLUDED — ' + record['excluded'] if record.get('excluded') else record['path'] or 'MISSING'}")
if errors:
    raise SystemExit('\n'.join(errors))
PY
pass 'Every non-excluded expected tool and PDK resource is installed'
