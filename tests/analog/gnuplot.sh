#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"
require_command gnuplot

work="$TEST_ROOT/run/analog/gnuplot"
mkdir -p "$work"
cd "$work"
env -u DISPLAY gnuplot -e 'set terminal svg; set output "plot.svg"; plot x*x'
grep -q '<svg' plot.svg || fail 'gnuplot did not produce an SVG'
pass 'gnuplot rendered an SVG without a display'
