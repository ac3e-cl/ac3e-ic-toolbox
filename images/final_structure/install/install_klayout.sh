#!/usr/bin/env bash
set -Eeuo pipefail
# Native Debian build copied from the independent klayout stage.
test -x /opt/klayout/bin/klayout
# KLayout embeds system libpython, so PATH alone does not expose venv packages.
# Its own path file avoids exporting PYTHONPATH into the Nix tool environments.
"$EDA_PYTHON/bin/python" -c 'import sys; print(repr([p for p in sys.path if p]))' \
    > /opt/klayout/bin/.python-paths.txt
ln -sf /opt/klayout/bin/klayout /usr/local/bin/klayout
klayout -v