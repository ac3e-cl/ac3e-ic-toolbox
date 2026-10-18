#!/usr/bin/env bash
set -Eeuo pipefail
# Run inside the container: bash /home/designer/shared/tests/gnucap.sh
command -v gnucap >/dev/null
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cat > "$work/divider.ckt" <<'NETLIST'
GNUCAP voltage divider
V1 in 0 10
R1 in out 1k
R2 out 0 1k
.print dc v(in) v(out)
.dc V1 10 10 1
.end
NETLIST
gnucap -b "$work/divider.ckt" > "$work/result.txt" 2>&1
cat "$work/result.txt"
# GNUCAP prints engineering suffixes; expected values here have none.
awk '
    $1 ~ /^[-+0-9.]+([eE][-+]?[0-9]+)?$/ && NF == 3 {
        if (($1-10)^2 < 1e-12 && ($2-10)^2 < 1e-12 && ($3-5)^2 < 1e-12) ok=1
    }
    END { if (!ok) { print "FAIL: expected source=10 V, input=10 V, output=5 V"; exit 1 } }
' "$work/result.txt"
echo 'PASS: GNUCAP resistor divider = 5 V'
