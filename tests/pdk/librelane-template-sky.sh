#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"
require_command librelane-template
mkdir -p "$TEST_ROOT/run/librelane-template-sky"
run="$(mktemp -d "$TEST_ROOT/run/librelane-template-sky/run.XXXXXXXX")"
printf 'Template evidence: %s/project/evidence\n' "$run"
librelane-template init sky "$run/project"
librelane-template run sky "$run/project" bash \
    "$TEST_ROOT/helpers/librelane-template-test.sh" sky "$TEST_ROOT" "${MAX_BUILD_JOBS:-2}"
pass "sky: pinned upstream template RTL, complete flow, metrics/GDS and gate-level simulation ($run)"
