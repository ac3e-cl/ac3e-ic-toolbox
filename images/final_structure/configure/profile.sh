# shellcheck shell=bash
if [ -n "${BASH_VERSION:-}" ]; then
    if [[ -f /opt/ac3e-ic-toolbox/config/ac3e-ic-toolbox-env.sh ]]; then
        source /opt/ac3e-ic-toolbox/config/ac3e-ic-toolbox-env.sh
    else
        source "${BASH_SOURCE[0]%/*}/ac3e-ic-toolbox-env.sh"
    fi
fi
