#!/usr/bin/env bash
set -Eeuo pipefail
# Official build procedure: https://codeberg.org/gnucap/gnucap/src/branch/develop/INSTALL
# Latest tagged snapshot: 20260729-dev (2026-07-29), pinned in manifest.json.
: "${TOOLS:?}" "${GNUCAP_NAME:?}" "${GNUCAP_REPO_URL:?}" "${GNUCAP_REPO_COMMIT:?}"
: "${GNUCAP_MODELGEN_REPO_URL:?}" "${GNUCAP_MODELGEN_REPO_COMMIT:?}"
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

# Build the matching model generator against the installed Gnucap headers and libraries.
git clone "$GNUCAP_MODELGEN_REPO_URL" "$work/modelgen"
git -C "$work/modelgen" checkout --detach "$GNUCAP_MODELGEN_REPO_COMMIT"
mkdir "$work/modelgen-build"
cd "$work/modelgen-build"
export PATH="$prefix/bin:$PATH"
export LD_LIBRARY_PATH="$prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
"$work/modelgen/configure" --prefix="$prefix"
# The snapshot's standalone build otherwise resolves its private headers
# relative to the parent of the source directory.
modelgen_cppflags="-I$work/modelgen/src"
make -j"${MAX_BUILD_JOBS:-2}" CPPFLAGS="$modelgen_cppflags"
make install CPPFLAGS="$modelgen_cppflags"

# Keep the core library discoverable even in Nix shells that clear LD_LIBRARY_PATH.
for command in gnucap gnucap-mg-vams; do
    mv "$prefix/bin/$command" "$prefix/bin/$command.real"
    cat > "$prefix/bin/$command" <<'WRAPPER'
#!/usr/bin/env bash
set -euo pipefail
prefix="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export LD_LIBRARY_PATH="$prefix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "${BASH_SOURCE[0]}.real" "$@"
WRAPPER
    chmod 755 "$prefix/bin/$command"
done
# The upstream binary is named gnucap-mg-vams; expose the documented CLI name too.
cat > "$prefix/bin/modelgen-verilog" <<'WRAPPER'
#!/usr/bin/env bash
exec "$(dirname -- "${BASH_SOURCE[0]}")/gnucap-mg-vams" "$@"
WRAPPER
chmod 755 "$prefix/bin/modelgen-verilog"
