# shellcheck shell=bash
# Shared environment: no cwd changes, compilation, or exported shell guards.
_ac3e_path_add() {
    local name="$1" value="$2" current="${!1-}"
    case ":$current:" in *":$value:"*) return 0 ;; esac
    printf -v "$name" '%s' "${current:+$current:}$value"
    export "$name"
}
_ac3e_setup() {
    local config tool directory status nix_active=false
    config="${BASH_SOURCE[0]%/*}"
    export TOOLS="${TOOLS:-/opt}" PDK_ROOT="${PDK_ROOT:-/opt/pdks}" DESIGNS="${DESIGNS:-/foss/designs}"
    export BASH_ENV="$config/ac3e-ic-toolbox-env.sh"
    if [[ -f "$HOME/.nix-profile/etc/profile.d/nix.sh" ]]; then
        source "$HOME/.nix-profile/etc/profile.d/nix.sh" || return $?
        nix_active=true
        unset LD_LIBRARY_PATH
        # Remove inherited common bins as well as avoiding new additions.
        local part clean=''
        local -a parts
        IFS=: read -r -a parts <<< "${PATH:-}"
        for part in "${parts[@]}"; do
            [[ "$part" != "$TOOLS/common/bin" ]] || continue
            clean="${clean:+$clean:}$part"
        done
        export PATH="$clean"
    fi
    for tool in cvc_rv gaw3-xschem iverilog magic netgen ngspice openvaf verilator xschem yosys openroad; do
        for directory in "$TOOLS/$tool"/*/bin; do
            [[ ! -d "$directory" ]] || _ac3e_path_add PATH "$directory"
        done
    done
    [[ ! -d "$TOOLS/yosys/bin" ]] || _ac3e_path_add PATH "$TOOLS/yosys/bin"
    if [[ "$nix_active" == false ]]; then
        _ac3e_path_add PATH "$TOOLS/common/bin"
        _ac3e_path_add LD_LIBRARY_PATH "$TOOLS/common/lib64"
        _ac3e_path_add LD_LIBRARY_PATH "$TOOLS/common/lib"
        local dependency
        for dependency in SWIG Eigen3 GTest LEMON spdlog ortools; do
            case " ${CMAKE_PACKAGE_ROOT_ARGS:-} " in
                *" -D ${dependency}_ROOT=$TOOLS/common "*) ;;
                *) export CMAKE_PACKAGE_ROOT_ARGS="${CMAKE_PACKAGE_ROOT_ARGS:+$CMAKE_PACKAGE_ROOT_ARGS }-D ${dependency}_ROOT=$TOOLS/common" ;;
            esac
        done
    fi
    export ORFS_DIR="$TOOLS/OpenROAD-flow-scripts" YOSYS_CMD=yosys OPENSTA_EXE=sta
    export OPENROAD_EXE="$(command -v openroad || :)" YOSYS_EXE="$(command -v yosys || :)"
    source "$config/pdk.sh" || return $?
    if [[ "${_AC3E_DESIGNINIT_DONE:-}" != "$BASHPID" ]]; then
        _AC3E_DESIGNINIT_DONE="$BASHPID"
        if [[ -f "$DESIGNS/.designinit" ]]; then
            source "$DESIGNS/.designinit" || { status=$?; return "$status"; }
        fi
    fi
    if [[ -n "${STD_CELL_LIBRARY:-}" ]]; then
        set_pdk "${PDK:-ihp-sg13g2}" "$STD_CELL_LIBRARY"
    else
        set_pdk "${PDK:-ihp-sg13g2}"
    fi
}
_ac3e_setup
