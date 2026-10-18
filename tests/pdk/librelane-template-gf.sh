#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"
require_command librelane-template
mkdir -p "$TEST_ROOT/run/librelane-template-gf"
run="$(mktemp -d "$TEST_ROOT/run/librelane-template-gf/run.XXXXXXXX")"
printf 'Template evidence: %s/project/evidence\n' "$run"
librelane-template init gf "$run/project"
librelane-template run gf "$run/project" bash \
    "$TEST_ROOT/helpers/librelane-template-test.sh" gf "$TEST_ROOT" "${MAX_BUILD_JOBS:-2}"
pass "gf: pinned upstream template RTL, complete flow, metrics/GDS and gate-level simulation ($run)"
