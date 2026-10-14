#!/usr/bin/env bash
# Install into a private virtualenv; never change EDA Python packages.
set -Eeuo pipefail
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
prefix=${AC3E_IC_TOOLBOX_MCP_HOME:-/opt/ac3e-ic-toolbox/mcp}
install -d -m 755 "$prefix/bin"
# uv is already installed by images/base/python_packages.sh.
uv venv --python /usr/bin/python3 "$prefix/venv"
uv pip install --python "$prefix/venv/bin/python" -r "$source_dir/requirements.txt"
install -m 644 "$source_dir/server.py" "$prefix/server.py"
install -m 644 "$source_dir/requirements.txt" "$prefix/requirements.txt"
install -m 755 "$source_dir/ac3e-ic-toolbox-mcp" "$prefix/bin/ac3e-ic-toolbox-mcp"
"$prefix/venv/bin/python" -I -c 'from mcp.server.fastmcp import FastMCP'
