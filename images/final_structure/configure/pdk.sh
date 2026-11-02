# shellcheck shell=bash
set_pdk() {
    if (( $# == 0 )); then
        printf 'Usage: sak-pdk <pdk> [<stdcell-lib>]\nAvailable PDKs:\n'
        local candidate
        for candidate in ihp-sg13g2 gf180mcuD; do
            [[ ! -d "${PDK_ROOT:-/opt/pdks}/$candidate" ]] || printf '%s\n' "$candidate"
        done
        return 0
    fi
    if (( $# > 2 )); then
        printf 'Usage: sak-pdk <pdk> [<stdcell-lib>]\n' >&2
        return 2
    fi
    local selected="$1" library root="${PDK_ROOT:-/opt/pdks}"
    case "$selected" in
        ihp-sg13g2) library=sg13g2_stdcell ;;
        gf180mcuD) library=gf180mcu_fd_sc_mcu7t5v0 ;;
        *) printf 'Unsupported PDK: %s\n' "$selected" >&2; return 2 ;;
    esac
    library="${2-$library}"
    if [[ -z "$library" || "$library" == */* || "$library" == . || "$library" == .. ]]; then
        printf 'Invalid standard-cell library: %s\n' "$library" >&2
        return 2
    fi
    if [[ ! -d "$root/$selected/libs.tech" || ! -d "$root/$selected/libs.ref/$library" ]]; then
        printf 'PDK or standard-cell library is not installed: %s/%s\n' "$selected" "$library" >&2
        return 2
    fi
    export PDK_ROOT="$root" PDK="$selected" PDKPATH="$root/$selected"
    export STD_CELL_LIBRARY="$library" SPICE_USERINIT_DIR="$PDKPATH/libs.tech/ngspice"
    export KLAYOUT_HOME="${HOME}/.klayout"
    export KLAYOUT_PATH="$KLAYOUT_HOME:$PDKPATH/libs.tech/klayout:${TOOLS:-/opt}/klayout/download"
    if [[ "$selected" == gf180mcuD ]]; then export GF_PDK_OPTION=D; else unset GF_PDK_OPTION; fi
    printf 'PDK set to %s\n' "$PDK"
}
sak-pdk() { set_pdk "$@"; }
