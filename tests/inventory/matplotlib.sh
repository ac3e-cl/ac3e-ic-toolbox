#!/usr/bin/env bash
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
MPLBACKEND=Agg MPLCONFIGDIR="$work/mpl" python - "$work/plot.png" <<'PY'
import os
from pathlib import Path
import sys
import matplotlib
import matplotlib.pyplot as plt

assert sys.prefix == os.environ['EDA_VENV'], sys.executable
assert Path(matplotlib.__file__).is_relative_to(sys.prefix), matplotlib.__file__
path = Path(sys.argv[1])
plt.plot([0, 1], [0, 1])
plt.savefig(path)
assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), path
print('Matplotlib', matplotlib.__version__)
PY
UV_CACHE_DIR="$work/uv" uv pip check --python "$EDA_VENV/bin/python"
pass 'Default EDA Python renders PNG with Matplotlib/Agg'
