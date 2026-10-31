#!/bin/bash
set -euo pipefail
export PATH="$(realpath "$TOOLS"/magic/*/bin):$PATH"
source /images/pdks/prepare_open_pdks.sh
prepare_open_pdks gf180mcu
trap 'rm -rf "$OPEN_PDKS_SOURCE"' EXIT
# The volare gf180 build's memory peak comes from magic converting large
# layouts, not from compiler throughput; several concurrent jobs can breach
# the CI builder's memory ceiling next to unrelated heavy stages. Bound it
# independently of the compiler budget and default to a single job.
PDK_BUILD_JOBS=${PDK_BUILD_JOBS:-1}
volare build --pdk=gf180mcu --use-repo-at "open_pdks=$OPEN_PDKS_SOURCE" -j "$PDK_BUILD_JOBS" "$OPEN_PDKS_REPO_COMMIT"
volare enable --pdk=gf180mcu "$OPEN_PDKS_REPO_COMMIT"

# open_pdks does not install the dropdown macros. Recover precisely the fd_pr
# reference from its pinned source (not a branch, and not the local git HEAD).
FD_PR_COMMIT=$(python3 - "$OPEN_PDKS_SOURCE/gf180mcu/gf180mcu.json" <<'PY'
import re, sys
text = open(sys.argv[1]).read().split('"reference":', 1)[1]
match = re.search(r'"gf180mcu_fd_pr":\s*"([0-9a-f]{40})"', text)
if not match:
    sys.exit('missing pinned fd_pr reference')
print(match[1])
PY
)
PR_SOURCE="$OPEN_PDKS_SOURCE/pinned-fd-pr"
git init "$PR_SOURCE"
git -C "$PR_SOURCE" fetch --depth=1 https://github.com/efabless/globalfoundries-pdk-libs-gf180mcu_fd_pr.git "$FD_PR_COMMIT"
git -C "$PR_SOURCE" checkout --detach FETCH_HEAD
test "$(git -C "$PR_SOURCE" rev-parse HEAD)" = "$FD_PR_COMMIT"
cp -a "$PR_SOURCE/rules/klayout/macros" "$PDK_ROOT/gf180mcuD/libs.tech/klayout/"
printf '%s\n' "$FD_PR_COMMIT" > "$PDK_ROOT/gf180mcuD/libs.tech/klayout/fd_pr_macros.commit"

# A is a private backing dependency of D. Hide only public variant links;
# retain backing, source caches, and every DRC/LVS resource until proven unused.
python3 /images/pdks/gf180_integrity.py hide "$PDK_ROOT"
TECH="$PDK_ROOT/gf180mcuD/libs.tech"
for resource in xschem/xschemrc ngspice/design.ngspice ngspice/sm141064.ngspice magic/gf180mcuD.magicrc klayout/tech/gf180mcu.lyt; do
    test -s "$TECH/$resource"
done
test -d "$PDK_ROOT/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu7t5v0"
python3 /images/pdks/gf180_integrity.py links "$PDK_ROOT/gf180mcuD"
