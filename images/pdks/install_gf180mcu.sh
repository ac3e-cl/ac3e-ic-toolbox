#!/bin/bash
# Download the complete, pinned Ciel artifact; never compile or mix legacy PDKs.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
: "${PDK_ROOT:?}" "${CIEL_VERSION:?}" "${GF180_PDK_COMMIT:?}"
[[ "$GF180_PDK_COMMIT" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid GF180_PDK_COMMIT' >&2; exit 1; }
CIEL_VERSION_OUTPUT=$(ciel --version)
if [[ "${CIEL_VERSION_OUTPUT%%$'\n'*}" != "Ciel v${CIEL_VERSION} "* ]]; then
    echo "Ciel version mismatch: expected $CIEL_VERSION, got $CIEL_VERSION_OUTPUT" >&2
    exit 1
fi
printf 'Ciel executable: %s\n%s\n' "$(command -v ciel)" "$CIEL_VERSION_OUTPUT"
# The upstream default downloads architecture-independent data, including
# analog models, macros, licenses and every SCL. No --build fallback is enabled.
ciel enable "$GF180_PDK_COMMIT" --pdk-root "$PDK_ROOT" --pdk gf180mcuD --include-libraries all
# Preserve the whole ciel/gf180mcu tree: D still links into private A resources.
python3 "$SCRIPT_DIR/gf180_integrity.py" hide "$PDK_ROOT"
python3 "$SCRIPT_DIR/gf180_integrity.py" ciel "$PDK_ROOT" "$GF180_PDK_COMMIT"
