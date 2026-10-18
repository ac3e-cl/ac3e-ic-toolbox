#!/usr/bin/env bash
set -euo pipefail
umask 022
if [[ $# != 3 ]]; then
    echo "Usage: $0 ENV_DIR SUPPORT_TOOLS_DIR TEMPLATE_DIR" >&2
    exit 2
fi
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=$(realpath -m -- "$1")
tools=$(realpath -- "$2")
template=$(realpath -- "$3")
expected=01d5d2814fa9dd61e9d211e0b235a4a592a9316a
[[ $(git -C "$tools" rev-parse HEAD) == "$expected" ]] || { echo "Wrong support-tools revision" >&2; exit 2; }
[[ -f $tools/requirements.txt && -f $template/test/requirements.txt ]] || { echo "Missing upstream requirements" >&2; exit 2; }
mkdir -p -- "$root"
nix --extra-experimental-features 'nix-command flakes' build --no-update-lock-file --max-jobs "${MAX_BUILD_JOBS:-2}" --cores "${MAX_BUILD_JOBS:-2}" "path:$here#default" --out-link "$root/nix"
unset PYTHONPATH NIX_PYTHONPATH PYTHONHOME
"$root/nix/bin/python3" -m venv --system-site-packages "$root/venv"
# Append the Nix closure, not prepend: support-tools' exact pins must win.
site="$root/venv/lib/python3.11/site-packages"
printf '%s\n' "$root/nix/lib/python3.11/site-packages" > "$site/librelane-nix.pth"
"$root/venv/bin/python" -m pip install -r "$tools/requirements.txt" -r "$template/test/requirements.txt" -r "$here/compat-requirements.txt"
"$root/venv/bin/python" -m pip check
printf 'export TTSKY_ENV=%q\n' "$root" > "$root/activate.sh"
cat >> "$root/activate.sh" <<'ACTIVATE'
unset PYTHONPATH NIX_PYTHONPATH PYTHONHOME
export PYTHONNOUSERSITE=1
export PATH="$TTSKY_ENV/venv/bin:$TTSKY_ENV/nix/bin:$PATH"
export LD_LIBRARY_PATH="$TTSKY_ENV/nix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
ACTIVATE
cat > "$root/run" <<'RUN'
#!/usr/bin/env bash
set -euo pipefail
root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
source "$root/activate.sh"
exec "$@"
RUN
chmod +x "$root/run"
chmod -R a+rX "$root/venv"
"$root/run" python -c 'import sys, librelane, numpy, klayout.db, cocotb; print(sys.version); print("LibreLane", librelane.__version__, librelane.__file__); print("numpy", numpy.__version__, "klayout", klayout.db.__version__, "cocotb", cocotb.__version__)'
"$root/run" yosys -y "$here/probe-embedded.py"
"$root/run" openroad -no_splash -exit -python "$here/probe-embedded.py"
