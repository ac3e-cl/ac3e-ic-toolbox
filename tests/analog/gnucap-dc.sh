#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"

require_command gnucap
[[ $(command -v gnucap) == /usr/local/bin/gnucap ]] || fail 'Gnucap must resolve to /usr/local/bin/gnucap'
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"
unset LD_LIBRARY_PATH GNUCAP_PLUGPATH
# Installed batch mode: see the pinned Gnucap tests/README.
cat > divider.ckt <<'EOF'
GNUCAP divider smoke test
V1 in 0 10
R1 in out 1k
R2 out 0 1k
.print dc v(in) v(out)
.dc V1 10 10 1
.end
EOF
gnucap -b divider.ckt > result.txt 2>&1 || { cat result.txt >&2; fail 'Gnucap batch run failed'; }
awk '$1 ~ /^[-+0-9.]+([eE][-+]?[0-9]+)?$/ && NF == 3 {
    if (($1-10)^2 < 1e-12 && ($2-10)^2 < 1e-12 && ($3-5)^2 < 1e-12) ok=1
} END { exit !ok }' result.txt || { cat result.txt >&2; fail 'Expected Gnucap divider output of 5 V'; }
pass 'Gnucap batch divider = 5 V'
