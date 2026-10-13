# shellcheck shell=bash
if [[ -f /opt/unic-cass/config/profile.sh ]]; then
    source /opt/unic-cass/config/profile.sh || return $?
else
    source "${BASH_SOURCE[0]%/*}/profile.sh" || return $?
fi
[[ $- == *i* ]] || return 0
PS1="\[\033[01;36m\]\u \[\033[01;35m\]\w\n\[\033[00m\]\$ "
alias ls="ls --color=auto -XF"
alias grep="grep --color=auto"
alias xschem='xschem --rcfile "$PDKPATH/libs.tech/xschem/xschemrc"'
alias xschemtcl='xschem --rcfile "$PDKPATH/libs.tech/xschem/xschemrc"'
alias magic='magic -rcfile "$PDKPATH"/libs.tech/magic/*.magicrc'
