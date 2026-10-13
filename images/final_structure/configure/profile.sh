# shellcheck shell=bash
if [ -n "${BASH_VERSION:-}" ]; then
    if [[ -f /opt/unic-cass/config/unic-cass-env.sh ]]; then
        source /opt/unic-cass/config/unic-cass-env.sh
    else
        source "${BASH_SOURCE[0]%/*}/unic-cass-env.sh"
    fi
fi
