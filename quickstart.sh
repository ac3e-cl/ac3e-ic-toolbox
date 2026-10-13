#!/usr/bin/env bash
# Bootstrap the main-branch launchers; never build the EDA image locally.
set -Eeuo pipefail

if (( $# > 1 )); then
    echo 'Usage: bash quickstart.sh [new-checkout-directory]' >&2
    exit 2
fi
destination=${1:-ac3e-ic-toolbox}
if [[ -e $destination || -L $destination ]]; then
    echo "Destination already exists: $destination. Use make start inside it, or choose a new directory." >&2
    exit 2
fi
for command in git make jq python3 docker; do
    command -v "$command" >/dev/null || { echo "Required command not found: $command" >&2; exit 2; }
done
[[ -n ${DISPLAY:-} ]] || { echo 'make start requires an X server and DISPLAY. Run from your desktop terminal.' >&2; exit 2; }
docker info >/dev/null || { echo 'Docker must be running and accessible to your user.' >&2; exit 2; }
git clone --depth 1 --single-branch --branch main -- \
    https://github.com/ac3e-cl/ac3e-ic-toolbox.git "$destination"
cd -- "$destination"
# Preserve a terminal for Docker even when invoked with curl ... | bash.
if [[ ! -t 0 ]]; then
    if ! { true </dev/tty; } 2>/dev/null; then
        echo "An interactive terminal is required. Run make start inside $destination." >&2
        exit 2
    fi
    exec make start </dev/tty
fi
exec make start
