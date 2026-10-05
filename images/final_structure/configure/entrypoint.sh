#!/usr/bin/env bash
set -Eeuo pipefail
if [[ -f /opt/unic-cass/config/unic-cass-env.sh ]]; then
    source /opt/unic-cass/config/unic-cass-env.sh
else
    source "${BASH_SOURCE[0]%/*}/unic-cass-env.sh"
fi
mode=auto
wait_requested=false
while (( $# )); do
    case "$1" in
        -s|--shell) mode=shell; shift ;;
        -X|--x11) mode=x11; shift ;;
        -V|--vnc) mode=vnc; shift ;;
        -w|--wait) wait_requested=true; shift ;;
        --) shift; break ;;
        -*) printf 'Unknown entrypoint option: %s\n' "$1" >&2; exit 2 ;;
        *) break ;;
    esac
done
if [[ "$mode" == auto ]]; then
    if (( $# )); then mode=shell
    elif [[ -n "${DISPLAY:-}" ]]; then mode=x11
    elif [[ "${ENABLE_GUI:-}" == 1 ]]; then mode=vnc
    else mode=shell
    fi
fi
if [[ "$mode" == shell || "$mode" == x11 ]]; then
    if [[ "$mode" == x11 && -z "${DISPLAY:-}" ]]; then
        printf 'X11 requires DISPLAY\n' >&2; exit 2
    fi
    if (( $# )); then exec "$@"; fi
    exec /bin/bash -i
fi
if [[ "${ENABLE_GUI:-}" != 1 ]]; then
    printf 'VNC unavailable: build image with ENABLE_GUI=1\n' >&2; exit 2
fi
launcher=''
for candidate in "${NO_VNC_HOME:-/opt/noVNC}/utils/novnc_proxy" "${NO_VNC_HOME:-/opt/noVNC}/utils/launch.sh"; do
    if [[ -x "$candidate" ]]; then launcher="$candidate"; break; fi
done
if [[ -z "$launcher" ]] || ! command -v vncserver >/dev/null || ! command -v vncpasswd >/dev/null || ! command -v startxfce4 >/dev/null; then
    printf 'VNC dependencies missing: build image with ENABLE_GUI=1\n' >&2; exit 2
fi
export DISPLAY=:1
mkdir -p "$HOME/.vnc"
if [[ -n "${VNC_PW:-}" ]]; then
    (umask 077; printf '%s\n' "$VNC_PW" | vncpasswd -f > "$HOME/.vnc/passwd")
elif [[ ! -s "$HOME/.vnc/passwd" ]]; then
    printf 'Set VNC_PW or provide ~/.vnc/passwd\n' >&2; exit 2
fi
pids=()
cleanup() {
    local pid
    trap - EXIT TERM INT
    for pid in "${pids[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then kill -TERM "$pid" 2>/dev/null || :; fi
    done
    for pid in "${pids[@]}"; do wait "$pid" 2>/dev/null || :; done
}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 130' INT
vncserver "$DISPLAY" -depth "${VNC_COL_DEPTH:-24}" -geometry "${VNC_RESOLUTION:-1280x800}" -localhost no -fg -xstartup startxfce4 &
pids+=("$!")
"$launcher" --vnc "localhost:${VNC_PORT:-5901}" --listen "${NO_VNC_PORT:-80}" &
pids+=("$!")
if (( $# )); then
    "$@" &
    pids+=("$!")
fi
# GUI children cannot outlive PID 1; supervise even without --wait.
status=0
wait -n "${pids[@]}" || status=$?
(( status != 0 )) || status=1
exit "$status"
