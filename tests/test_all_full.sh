#!/usr/bin/env bash
# Explicit opt-in suite for long-running integration tests only.
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ $# == 0 ]] || { printf 'Usage: %s\n' "$0" >&2; exit 2; }
exec bash "$TEST_ROOT/run_all.sh" --long-only
