#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"
require_command librelane-template
mkdir -p "$TEST_ROOT/run/librelane-template-ihp"
run="$(mktemp -d "$TEST_ROOT/run/librelane-template-ihp/run.XXXXXXXX")"
printf 'Template evidence: %s/project/evidence\n' "$run"
librelane-template init ihp "$run/project"
librelane-template run ihp "$run/project" bash \
    "$TEST_ROOT/helpers/librelane-template-test.sh" ihp "$TEST_ROOT" "${MAX_BUILD_JOBS:-2}"
pass "ihp: pinned upstream template RTL, complete flow, metrics/GDS and gate-level simulation ($run)"
