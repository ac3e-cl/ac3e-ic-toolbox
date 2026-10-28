#!/usr/bin/env bash
# Real-image gate: user Python, Ubuntu Python and embedded runtimes stay separate.
set -Eeuo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source "$TEST_ROOT/common.sh"
load_design_env
for executable in python python3 python3.11 uv jupyter; do
    require_command "$executable"
done
for executable in python python3 python3.11; do
    "$executable" - <<'PY'
import os
import sys
assert sys.version_info[:2] == (3, 11), sys.version
assert sys.prefix == os.environ['EDA_VENV'], (sys.executable, sys.prefix)
print(sys.executable, sys.version.split()[0])
PY
done
/usr/bin/python3 - <<'PY'
import sys
assert sys.version_info[:2] == (3, 10), sys.version
print('Ubuntu system Python retained:', sys.executable, sys.version.split()[0])
PY
python - <<'PY'
import bz2
import ctypes
import gi
import ipykernel
import jupyterlab
import klayout.db
import lzma
import numpy
import pandas
import scipy
import sqlite3
import ssl
import tkinter
print('EDA Python and standard-library imports passed')
PY
uv pip check --python "$EDA_VENV/bin/python"
pass 'Python 3.11 user environment; Ubuntu Python preserved; EDA dependencies consistent'
