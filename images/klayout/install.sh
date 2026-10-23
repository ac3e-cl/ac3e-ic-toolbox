#!/usr/bin/env bash
# Build the manifest-pinned GUI and embedded interpreters against Debian's ABI.
set -Eeuo pipefail
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
prefix="$TOOLS/$KLAYOUT_NAME/bin"
git clone --filter=blob:none "$KLAYOUT_REPO_URL" "$work/source"
git -C "$work/source" checkout --detach "$KLAYOUT_REPO_COMMIT"
cd "$work/source"
git submodule update --init --recursive
mkdir -p "$prefix"
./build.sh -release -option "-j${MAX_BUILD_JOBS:-2}" \
    -python /usr/bin/python3 -ruby /usr/bin/ruby -bin "$prefix"
"$prefix/klayout" -v
