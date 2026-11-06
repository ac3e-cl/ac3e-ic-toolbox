#!/usr/bin/env bash
# Exercise the actual Nix-backed precheck, not a substituted CLI fixture.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TEST_ROOT="$(dirname "$SCRIPT_DIR")"
source "$TEST_ROOT/common.sh"
load_design_env
require_command gf180-precheck
mkdir -p "$TEST_ROOT/run/gf180-precheck"
run=$(mktemp -d "$TEST_ROOT/run/gf180-precheck/run.XXXXXXXX")
python3 - "$run/invalid.gds" <<'PY'
import sys
import klayout.db as db
layout = db.Layout()
layout.dbu = 0.001
layer = layout.layer(34, 0)
for name in ('invalid', 'extra_top'):
    layout.create_cell(name).shapes(layer).insert(db.Box(0, 0, 1000, 1000))
layout.write(sys.argv[1])
PY
if gf180-precheck "$run" --input invalid.gds --output rejected.oas \
    --id FFFFFFFF --slot 1x1 --top invalid --run-tag invalid-top > "$run/precheck.log" 2>&1; then
    fail 'precheck accepted a layout with two top-level cells'
fi
python3 - "$run" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
logs = [root / 'precheck.log', *root.glob('runs/**/*log')]
text = '\n'.join(p.read_text(errors='replace') for p in logs if p.is_file())
assert 'More than one top-level cell' in text, text[-12000:]
assert not (root / 'rejected.oas').exists(), 'failed precheck wrote a final layout'
assert 'ModuleNotFoundError' not in text, text[-12000:]
assert 'Traceback' not in text, text[-12000:]
PY
pass "real GF precheck rejects multiple top-level cells ($run)"
