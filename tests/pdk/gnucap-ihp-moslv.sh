#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"

require_command gnucap
require_command gnucap-conf
tech="${PDK_ROOT:-/opt/pdks}/ihp-sg13g2/libs.tech/gnucap"
[[ -s "$tech/plugins/models/sg13g2_moslv_paramset.so" ]] || fail 'IHP MOSLV plugin was not precompiled'
export GNUCAP_PLUGPATH="$tech/plugins/models:$(gnucap-conf --pkglibdir)"
export GNUCAP_INCLUDEPATH="$tech/models:$(gnucap-conf --includedir)"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"
cat > nmos.gc <<'NETLIST'
load mgsim
verilog
load sg13g2_moslv_paramset.so
include sg13g2_moslv_module.va
ground gnd;
include cornerMOSlv.va
moslv_tt corner_moslv();
sg13_lv_nmos #(.w(1.0e-6), .l(0.13e-6), .ng(1), .mm_ok(0)) XM1(nd, ng, gnd, gnd);
spice
Vgs ng gnd 0
Vds nd gnd 0
.print dc ids(XM1.*) v(nd)
.dc Vds 0 0.02 0.01 > dcnmos.txt
NETLIST
gnucap nmos.gc </dev/null > gnucap.log 2>&1
if grep -Eiq '\? |plugin not found|undefined symbol' gnucap.log || [[ ! -s dcnmos.txt ]] ||
   ! awk 'NR == 1 && /ids\(XM1/ { header=1 }
          $1 == 0.01 && $2 > 1.7e-12 && $2 < 1.8e-12 { current=1 }
          END { exit !(header && current) }' dcnmos.txt; then
    cat gnucap.log >&2
    [[ ! -f dcnmos.txt ]] || cat dcnmos.txt >&2
    fail 'IHP MOSLV sweep did not produce the expected drain current'
fi
pass 'Precompiled IHP MOSLV model: nominal drain current at Vds=10 mV'
