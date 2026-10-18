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
assert set(pins) == {'ihp', 'gf', 'sky'}, 'Expected all three template pins'
for key, value in pins.items():
    for field in ('commit', 'librelaneCommit', 'pdkCommit'):
        assert re.fullmatch('[0-9a-f]{40}', value[field]), (key, field)
    print('\t'.join([key, value['url'], value['commit'], value['librelaneCommit'], value['pdkCommit']]))
PY
)
mapfile -t rows <<< "$rows_text"
[[ ${#rows[@]} == 3 ]] || { echo 'Expected all three template pins' >&2; exit 1; }
for row in "${rows[@]}"; do
    IFS=$'\t' read -r key url commit librelane_commit pdk_commit <<< "$row"
    git clone --no-checkout "$url" "$root/src/$key"
    git -C "$root/src/$key" checkout --detach "$commit"
    git -C "$root/src/$key" submodule update --init --recursive
    if [[ "$key" == sky ]]; then
        tools_row=$(python3 - "$manifest" <<'PY'
import json, re, sys
pin = json.load(open(sys.argv[1]))['librelaneTemplates']['sky']
assert re.fullmatch('[0-9a-f]{40}', pin['supportToolsCommit'])
print(pin['supportToolsUrl'] + '\t' + pin['supportToolsCommit'])
PY
)
        IFS=$'\t' read -r tools_url tools_commit <<< "$tools_row"
        git clone --no-checkout "$tools_url" "$root/src/sky/tt"
        git -C "$root/src/sky/tt" checkout --detach "$tools_commit"
        git -C "$root/src/sky/tt" submodule update --init --recursive
        cp -a "$(dirname -- "${BASH_SOURCE[0]}")/sky" "$root/sky"
        python3 - "$root/sky/flake.lock" "$librelane_commit" <<'PY'
import json, sys
assert json.load(open(sys.argv[1]))['nodes']['librelane']['locked']['rev'] == sys.argv[2]
PY
        env -u BASH_ENV -u PYTHONPATH -u LD_LIBRARY_PATH \
            bash "$root/sky/bootstrap.sh" "$root/sky-env" "$root/src/sky/tt" "$root/src/sky"
        printf 'source %q\n' "$root/sky-env/activate.sh" > "$root/activate/sky.sh"
        "$root/sky-env/run" ciel enable --pdk-family sky130 --pdk-root "$root/pdks/sky" "$pdk_commit"
        continue
    fi
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
