#!/usr/bin/env bash
set -Eeuo pipefail
# Official build procedure: https://codeberg.org/gnucap/gnucap/src/branch/develop/INSTALL
# Latest tagged snapshot: 20260729-dev (2026-07-29), pinned in manifest.json.
: "${TOOLS:?}" "${GNUCAP_NAME:?}" "${GNUCAP_REPO_URL:?}" "${GNUCAP_REPO_COMMIT:?}"
prefix="$TOOLS/$GNUCAP_NAME/$GNUCAP_REPO_COMMIT"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
git clone "$GNUCAP_REPO_URL" "$work/source"
git -C "$work/source" checkout --detach "$GNUCAP_REPO_COMMIT"
mkdir "$work/build"
cd "$work/build"
"$work/source/configure" --prefix="$prefix"
make -j"${MAX_BUILD_JOBS:-2}"
make install
# Keep the core library discoverable even in Nix shells that clear LD_LIBRARY_PATH.
mv "$prefix/bin/gnucap" "$prefix/bin/gnucap.real"
cat > "$prefix/bin/gnucap" <<'WRAPPER'
#!/usr/bin/env bash
set -euo pipefail
prefix="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export LD_LIBRARY_PATH="$prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$prefix/bin/gnucap.real" "$@"
WRAPPER
chmod 755 "$prefix/bin/gnucap"
