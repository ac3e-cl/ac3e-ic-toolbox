#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"
load_design_env
require_command nix
RUN_DIR="$TEST_ROOT/run/nix"
mkdir -p "$RUN_DIR"
nix --extra-experimental-features nix-command eval --offline --json --expr '{ result = builtins.add 1 (builtins.add 2 3); }' > "$RUN_DIR/result.json"
python3 - "$RUN_DIR/result.json" <<'PY'
import json
import sys
with open(sys.argv[1]) as stream:
    assert json.load(stream) == {'result': 6}
PY
pass 'Nix offline expression evaluation'
