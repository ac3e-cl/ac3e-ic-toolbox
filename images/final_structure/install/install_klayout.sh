#!/bin/bash
set -Eeuo pipefail

wget -nv -O klayout_installer.deb "${KLAYOUT_DOWNLOAD}"
dpkg -i klayout_installer.deb
rm klayout_installer.deb

# The Ubuntu 22 .deb embeds libpython3.10, independently of the user Python.
# Pinned GF PCells require gdsfactory.typings and gf.geometry (pre-8 API).
# Install only their direct dependencies and resolver-required transitive closure,
# not the full user EDA/notebook environment.
pcell_venv=/opt/klayout-pcells
uv venv --python /usr/bin/python3.10 "$pcell_venv"
uv pip install --python "$pcell_venv/bin/python" --strict --no-cache \
    "numpy<2" "gdsfactory<8"
uv pip check --python "$pcell_venv/bin/python"
install -m 0755 "$(dirname "${BASH_SOURCE[0]}")/klayout" /usr/local/bin/klayout
