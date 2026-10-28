#!/usr/bin/env bash
# Build a user Python alongside Ubuntu's system interpreter.
set -Eeuo pipefail
: "${PYTHON_VERSION:?PYTHON_VERSION is required}"
: "${PYTHON_SOURCE_SHA256:?PYTHON_SOURCE_SHA256 is required}"
[[ "$PYTHON_VERSION" =~ ^3\.11\.[0-9]+$ ]]
[[ "$PYTHON_SOURCE_SHA256" =~ ^[0-9a-f]{64}$ ]]
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"
curl --fail --location --retry 5 \
    "https://www.python.org/ftp/python/$PYTHON_VERSION/Python-$PYTHON_VERSION.tar.xz" \
    --output python.tar.xz
printf '%s  python.tar.xz\n' "$PYTHON_SOURCE_SHA256" | sha256sum --check --strict
tar -xf python.tar.xz
cd "Python-$PYTHON_VERSION"
# RPATH keeps libpython independent of the shell's LD_LIBRARY_PATH (including Nix).
LDFLAGS='-Wl,-rpath,/opt/python/lib' ./configure \
    --prefix=/opt/python --enable-shared --with-ensurepip=install
make -j "${MAX_BUILD_JOBS:-2}"
make altinstall
/opt/python/bin/python3.11 -c \
    'import ssl, sqlite3, bz2, lzma, ctypes, readline, tkinter, uuid; import sys; assert sys.version_info[:2] == (3, 11)'
find /opt/python -type d -name __pycache__ -prune -exec rm -rf {} +
