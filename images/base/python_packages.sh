#!/bin/bash

set -Eeuxo pipefail

/usr/bin/python3 -m pip install --no-cache-dir uv
: "${EDA_VENV:=/opt/eda-venv}"
uv venv --python /opt/python/bin/python3.11 --seed "$EDA_VENV"

# Increase timeout for large package downloads
export UV_HTTP_TIMEOUT=300

uv pip install --python "$EDA_VENV/bin/python" --strict \
    "numpy<2" \
    gdsfactory \
    glayout \
    cace \
    pandas \
    ojson \
    networkx \
    pytest \
    scipy \
    gdstk \
    svgutils \
    prettyprinttree \
    pyspice \
    volare==0.18.1 \
    spyci \
    jupyter \
    jupyterlab \
    ipython \
    ipykernel \
    ipywidgets \
    docopt \
    klayout \
    pygmid \
    kfactory \
    ruff \
    click \
    "pygobject<3.52.0" \
    xdot

uv pip check --python "$EDA_VENV/bin/python"
"$EDA_VENV/bin/python" -m ipykernel install --prefix "$EDA_VENV" \
    --name python311 --display-name 'Python 3.11 (EDA)'

# Cleanup: Remove Python cache files
find /usr/local -name "*.pyc" -delete 2>/dev/null || true
find /usr/local -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find ~/.cache -type f -delete 2>/dev/null || true
rm -rf ~/.cache/pip ~/.cache/uv 2>/dev/null || true