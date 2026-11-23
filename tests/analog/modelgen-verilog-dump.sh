#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"

require_command modelgen-verilog
[[ $(command -v modelgen-verilog) == /usr/local/bin/modelgen-verilog ]] || fail 'Modelgen must resolve to /usr/local/bin/modelgen-verilog'
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"
unset LD_LIBRARY_PATH GNUCAP_PLUGPATH
# Standalone smoke from the pinned Modelgen README and tests/MakeBase dump recipe.
printf 'module toolbox_dump;\nendmodule\n' > smoke.vams
modelgen-verilog --dump smoke.vams > smoke.dump 2> smoke.err || { cat smoke.err >&2; fail 'Modelgen dump failed'; }
grep -Eq '^[[:space:]]*module[[:space:]]+toolbox_dump([[:space:](;]|$)' smoke.dump &&
    grep -Eq '^[[:space:]]*endmodule([[:space:]]|$)' smoke.dump || {
        cat smoke.err smoke.dump >&2; fail 'Expected a parsed toolbox_dump module';
    }
pass 'Modelgen dumped a Verilog-AMS module'
