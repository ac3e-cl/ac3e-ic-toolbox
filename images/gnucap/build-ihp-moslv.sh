#!/usr/bin/env bash
set -Eeuo pipefail

tech="${1:?IHP libs.tech directory required}"
out="${2:?output directory required}"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

# Only the generated MOSLV plugin is exported; never modify the source PDK.
cp -R "$tech/gnucap/models" "$tech/gnucap/gnucap.mk" "$work/"
make -C "$work/models" -j1 IHP_VERILOG_DIR="$tech/verilog-a" sg13g2_moslv_paramset
plugin="$work/plugins/models/sg13g2_moslv_paramset.so"
test -s "$plugin"
install -D -m 0755 "$plugin" "$out/sg13g2_moslv_paramset.so"
