#!/usr/bin/env bash
# Build-time only. Preserve the upstream lock and materialize a separate shell/PDK.
set -euo pipefail
manifest=${1:?Usage: install-precheck.sh MANIFEST}
root="${LIBRELANE_TEMPLATES_ROOT:-/opt/librelane-templates}"
scripts=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
row=$(python3 "$scripts/precheck-pins.py" "$manifest")
IFS=$'\t' read -r url commit librelane_commit pdk_commit ciel_version ciel_commit <<< "$row"
mkdir -p "$root"/{src,profiles,pdks,activate,metadata}
root=$(realpath -- "$root")
source_dir="$root/src/gf-precheck"
git clone --no-checkout "$url" "$source_dir"
git -C "$source_dir" checkout --detach "$commit"
[[ $(git -C "$source_dir" rev-parse HEAD) == "$commit" ]]
git -C "$source_dir" submodule update --init --recursive
python3 "$scripts/precheck-pins.py" "$manifest" "$source_dir" >/dev/null
lock_hash=$(sha256sum "$source_dir/flake.lock")
# Use this precheck's flake, never the template profile (extra QR/Pillow packages).
env -u BASH_ENV -u PYTHONPATH -u PYTHONHOME -u LD_LIBRARY_PATH \
    -u PDK_ROOT -u PDK -u STD_CELL_LIBRARY \
    nix develop --accept-flake-config --no-update-lock-file \
    --max-jobs "${MAX_BUILD_JOBS:-2}" --cores "${MAX_BUILD_JOBS:-2}" \
    "$source_dir" --profile "$root/profiles/gf-precheck" --command true
env -u BASH_ENV -u PYTHONPATH -u PYTHONHOME -u LD_LIBRARY_PATH \
    nix print-dev-env --offline "$root/profiles/gf-precheck" > "$root/activate/gf-precheck.sh"
# Upstream's precheck Makefile still uses --pdk-family. Use Ciel 3.1.0's actual
# interface directly, with all libraries; do not edit the upstream Makefile/lock.
env -i HOME="$HOME" USER="${USER:-designer}" PATH=/usr/bin:/bin \
    /bin/bash --noprofile --norc -c '
        set -euo pipefail
        source "$1"
        eval "${shellHook:-}"
        export PDK_ROOT="$2" PDK=gf180mcuD
        command -v ciel
        version=$(ciel --version)
        printf "%s\n" "$version"
        [[ $version =~ (^|[^0-9.])3\.1\.0([^0-9.]|$) ]] || { echo "Unexpected Ciel version" >&2; exit 1; }
        ciel enable "$3" --pdk-root "$2" --pdk gf180mcuD --include-libraries all
        [[ -d "$2/gf180mcuD" ]]
    ' precheck-install "$root/activate/gf-precheck.sh" "$root/pdks/gf-precheck" "$pdk_commit" \
    > "$root/metadata/gf-precheck.txt"
[[ $(sha256sum "$source_dir/flake.lock") == "$lock_hash" ]] || {
    echo 'Precheck lock changed during installation' >&2; exit 1;
}
