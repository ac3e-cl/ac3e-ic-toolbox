#!/usr/bin/env bash
# Private headless display; never expose a VNC listener. Sourced by GUI tests.
gui_pids=()
gui_cleanup() {
    local pid i
    for pid in "${gui_pids[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    for i in {1..20}; do
        local alive=0
        for pid in "${gui_pids[@]}"; do
            if kill -0 "$pid" 2>/dev/null; then alive=1; fi
        done
        (( alive == 0 )) && break
        sleep 0.1
    done
    for pid in "${gui_pids[@]}"; do
        kill -KILL "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    done
}
trap gui_cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
start_gui_display() {
    require_command xdpyinfo
    export DISPLAY=:97
    if command -v Xvfb >/dev/null 2>&1; then
        Xvfb "$DISPLAY" -screen 0 1024x768x24 -nolisten tcp >"$run/display.log" 2>&1 &
    elif command -v Xvnc >/dev/null 2>&1; then
        # The released GUI image includes TigerVNC, not Xvfb.
        Xvnc "$DISPLAY" -geometry 1024x768 -depth 24 -nolisten tcp -rfbport -1 >"$run/display.log" 2>&1 &
    else
        fail 'headless GUI requires Xvfb or Xvnc'
    fi
    local pid=$!
    gui_pids+=("$pid")
    for _ in {1..50}; do
        kill -0 "$pid" 2>/dev/null || fail 'headless display exited before readiness'
        if xdpyinfo >"$run/display-info.log" 2>&1; then return; fi
        sleep 0.1
    done
    fail 'headless display readiness deadline exceeded'
}
