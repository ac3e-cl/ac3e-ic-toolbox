#!/usr/bin/env bash
set -Eeuo pipefail
# Official build procedure: https://codeberg.org/gnucap/gnucap/src/branch/develop/INSTALL
# Snapshot: 20260729-dev, pinned in manifest.json.
: "${GNUCAP_REPO_URL:?}" "${GNUCAP_REPO_COMMIT:?}"
: "${GNUCAP_MODELGEN_REPO_URL:?}" "${GNUCAP_MODELGEN_REPO_COMMIT:?}"
prefix=/usr/local
dist=/gnucap-dist
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

git clone "$GNUCAP_REPO_URL" "$work/source"
git -C "$work/source" checkout --detach "$GNUCAP_REPO_COMMIT"
mkdir "$work/build"
cd "$work/build"
"$work/source/configure" --prefix="$prefix"
make -j"${MAX_BUILD_JOBS:-2}"
make install DESTDIR="$dist"

# Modelgen configure/build calls the installed gnucap-conf. Expose the staged
# core at its real prefix in the builder; only the dist tree is exported.
cp -a "$dist$prefix/." "$prefix/"
ldconfig
export PATH="$prefix/bin:$PATH"
test "$(command -v gnucap-conf)" = "$prefix/bin/gnucap-conf"

git clone "$GNUCAP_MODELGEN_REPO_URL" "$work/modelgen"
git -C "$work/modelgen" checkout --detach "$GNUCAP_MODELGEN_REPO_COMMIT"
mkdir "$work/modelgen-build"
cd "$work/modelgen-build"
"$work/modelgen/configure" --prefix="$prefix"
# The standalone snapshot needs the private source-header directory explicitly.
modelgen_cppflags="-I$work/modelgen/src"
make -j"${MAX_BUILD_JOBS:-2}" CPPFLAGS="$modelgen_cppflags"
make install DESTDIR="$dist" CPPFLAGS="$modelgen_cppflags"
ln -s gnucap-mg-vams "$dist$prefix/bin/modelgen-verilog"

cp -a "$dist$prefix/." "$prefix/"
ldconfig
for command in gnucap gnucap-conf gnucap-mg-vams modelgen-verilog; do
    test -x "$dist$prefix/bin/$command"
done
