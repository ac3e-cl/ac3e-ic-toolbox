#!/usr/bin/env bash
# Shared helpers for in-container tests. Source this file from each test script.

pass() {
	printf 'INFO: %s\t [PASS]\n' "$1"
}

fail() {
	printf 'ERROR: %s\t [FAIL]\n' "$1" >&2
	exit 1
}

load_design_env() {
	export HOME="${HOME:-/home/designer}"
	# shellcheck disable=SC1091
	source /opt/unic-cass/config/unic-cass-env.sh
}

require_command() {
	if ! command -v "$1" >/dev/null 2>&1; then
		fail "required command not found: $1"
	fi
}
