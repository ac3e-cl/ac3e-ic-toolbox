#!/usr/bin/env bash
# Materialize immutable upstream templates, their Nix shells and private PDKs.
set -euo pipefail
manifest=${1:?Usage: install.sh MANIFEST}
root="${LIBRELANE_TEMPLATES_ROOT:-/opt/librelane-templates}"
mkdir -p "$root"/{src,profiles,pdks,activate}
cp "$manifest" "$root/manifest.json"
source /home/designer/.nix-profile/etc/profile.d/nix.sh
rows_text=$(python3 - "$manifest" <<'PY'
import json, re, sys
pins = json.load(open(sys.argv[1]))['librelaneTemplates']
assert set(pins) == {'ihp', 'gf'}, 'Expected IHP and GF template pins only'
for key, value in pins.items():
    for field in ('commit', 'librelaneCommit', 'pdkCommit'):
        assert re.fullmatch('[0-9a-f]{40}', value[field]), (key, field)
    print('\t'.join([key, value['url'], value['commit'], value['librelaneCommit'], value['pdkCommit']]))
PY
)
mapfile -t rows <<< "$rows_text"
[[ ${#rows[@]} == 2 ]] || { echo 'Expected IHP and GF template pins only' >&2; exit 1; }
for row in "${rows[@]}"; do
    IFS=$'\t' read -r key url commit librelane_commit pdk_commit <<< "$row"
    git clone --no-checkout "$url" "$root/src/$key"
    git -C "$root/src/$key" checkout --detach "$commit"
    git -C "$root/src/$key" submodule update --init --recursive
    python3 - "$root/src/$key" "$librelane_commit" "$pdk_commit" <<'PY'
import json, pathlib, re, sys
root = pathlib.Path(sys.argv[1])
assert json.loads((root / 'flake.lock').read_text())['nodes']['librelane']['locked']['rev'] == sys.argv[2]
assert re.search(r'^PDK_COMMIT \?= (\w+)$', (root / 'Makefile').read_text(), re.M)[1] == sys.argv[3]
PY
    env -u BASH_ENV -u PYTHONPATH -u LD_LIBRARY_PATH \
        nix develop --accept-flake-config --no-update-lock-file \
        --max-jobs "${MAX_BUILD_JOBS:-2}" --cores "${MAX_BUILD_JOBS:-2}" \
        "$root/src/$key" --profile "$root/profiles/$key" --command true
    nix print-dev-env --offline "$root/profiles/$key" > "$root/activate/$key.sh"
    env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin \
        /home/designer/.nix-profile/bin/nix --extra-experimental-features 'nix-command flakes' \
        develop --offline "$root/profiles/$key" --command bash --noprofile --norc -c \
        'cd "$1"; make clone-pdk PDK_ROOT="$2"' template-install "$root/src/$key" "$root/pdks/$key"
done
