#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
mode=${1:-shell}; shift || :
json=0
if [[ ${1:-} == --print-json ]]; then json=1; shift; fi
# Only literal KEY=value is accepted: never source/eval project configuration.
env_file=${ENV_FILE:-$root/.env}
if [[ -f $env_file ]]; then
    while IFS= read -r line || [[ -n $line ]]; do
        line=${line%$'\r'}
        [[ $line =~ ^[[:space:]]*(#.*)?$ ]] && continue
        [[ $line =~ ^([A-Za-z_][A-Za-z_0-9]*)=(.*)$ ]] || { echo 'Invalid .env syntax (expected KEY=value)' >&2; exit 2; }
        key=${BASH_REMATCH[1]}; value=${BASH_REMATCH[2]}
        if [[ $value == \"* || $value == \'* ]]; then
            quote=${value:0:1}
            [[ ${#value} -ge 2 && ${value: -1} == "$quote" ]] || { echo 'Unterminated .env value' >&2; exit 2; }
            value=${value:1:${#value}-2}
        fi
        [[ -v $key ]] || export "$key=$value"
    done < "$env_file"
fi
registry=${DOCKER_REGISTRY-$(jq -r .image.registry "$root/manifest.json")}
namespace=${DOCKER_USER-$(jq -r .image.namespace "$root/manifest.json")}
image=${DOCKER_IMAGE-$(jq -r .image.name "$root/manifest.json")}
tag=${DOCKER_TAG-$(jq -r .release.version "$root/manifest.json")}
reference=$image:$tag
[[ -z $namespace ]] || reference=$namespace/$reference
[[ -z $registry || $registry == docker.io ]] || reference=$registry/$reference
if [[ -n ${DESIGNS:-} && -n ${SHARED_DIR:-} && $DESIGNS != "$SHARED_DIR" ]]; then
    echo 'DESIGNS and SHARED_DIR conflict' >&2; exit 2
fi
designs=${DESIGNS:-${SHARED_DIR:-$root/shared}}
[[ $designs == /* ]] || designs=$PWD/$designs
[[ $designs != *,* ]] || { echo 'Docker bind paths cannot contain commas' >&2; exit 2; }
uid=${CONTAINER_USER:-${USER_ID:-$(id -u)}}
gid=${CONTAINER_GROUP:-${USER_GROUP:-$(id -g)}}
[[ -z ${ROOT:-} ]] || { uid=0; gid=0; }
[[ $uid =~ ^[0-9]+$ && $gid =~ ^[0-9]+$ ]] || { echo 'UID/GID must be numeric' >&2; exit 2; }
identity_mode=$mode
case $mode in attach|rm|print) identity_mode=x;; esac
name=${CONTAINER_NAME:-unic-cass-tools_${identity_mode}_uid_${uid}}

argv=(docker run --name "$name" --user "$uid:$gid" --mount "type=bind,source=$designs,target=/home/designer/shared" --mount "type=bind,source=$root/tests,target=/home/designer/tests" --env SHELL=/bin/bash --env "PDK=${PDK:-ihp-sg13g2}")
for setting in STD_CELL_LIBRARY VNC_PW VNC_RESOLUTION TEST_TIMEOUT; do
    [[ ! -v $setting ]] || argv+=(--env "$setting=${!setting}")
done
port() {
    local value=$1 target=$2
    [[ $value =~ ^[0-9]{1,5}$ ]] && (( 10#$value <= 65535 )) || { echo 'Invalid host port' >&2; exit 2; }
    (( 10#$value == 0 )) || argv+=(-p "127.0.0.1:$((10#$value)):$target")
}
case $mode in
    shell|x|attach) argv+=(-it);;
    vnc|jupyter) argv+=(-d);;
    test) argv+=(--rm);;
    build|print|pull|push|rm|devcontainer) ;;
    *) echo 'Unknown launcher mode' >&2; exit 2;;
esac
case $mode in
    x|attach)
        [[ -n ${DISPLAY:-} ]] || { echo 'X mode requires DISPLAY' >&2; exit 2; }
        argv+=(--mount type=bind,source=/tmp/.X11-unix,target=/tmp/.X11-unix,readonly --env "DISPLAY=$DISPLAY")
        auth=${XAUTHORITY:-$HOME/.Xauthority}
        if [[ -f $auth ]]; then argv+=(--mount "type=bind,source=$auth,target=/tmp/.Xauthority,readonly" --env XAUTHORITY=/tmp/.Xauthority); fi;;
    vnc) port "${VNC_PORT:-5901}" 5901; port "${HTTP_PORT:-${WEBSERVER_PORT:-8080}}" 80;;
    jupyter) port "${JUPYTER_PORT:-8888}" 8888;;
esac
if [[ -n ${DOCKER_EXTRA_PARAMS:-} ]]; then
    read -r -a extra <<< "$DOCKER_EXTRA_PARAMS"
    argv+=("${extra[@]}")
fi
# A container-private home avoids changing either image ownership or host data.
# Keep the installed single-user Nix profile as a read-only executable source.
# Image prerequisite: /home/designer must be traversable by arbitrary UIDs.
bootstrap='set -eu; ln -s /home/designer/.nix-profile "$HOME/.nix-profile"; cp /home/designer/.bashrc "$HOME/.bashrc"; exec /entrypoint.sh "$@"'
argv+=(--tmpfs "/tmp/unic-cass-home:rw,nosuid,nodev,mode=0700,uid=$uid,gid=$gid" --env HOME=/tmp/unic-cass-home --entrypoint /bin/bash)
argv+=("$reference" --noprofile --norc -c "$bootstrap" unic-cass-home)
case $mode in
    shell|x|attach) argv+=(--shell); if (( $# )); then argv+=("$@"); else argv+=(/bin/bash); fi;;
    vnc) argv+=(--vnc --wait "$@");;
    jupyter) argv+=(--shell jupyter lab --no-browser --ip=0.0.0.0 --notebook-dir=/foss/designs "$@");;
    test) argv+=(--shell bash /home/designer/tests/run_all.sh "$@");;
    build) if [[ -n ${STAGE:-} ]]; then argv=("$root/build/build-stage.sh" "$STAGE"); else argv=("$root/build/build-image.sh"); fi;;
    print) ;;
    pull) argv=(docker image pull "$reference");;
    push) argv=(docker image push "$reference");;
    rm) argv=(docker container rm "$name");;
    devcontainer) argv=(code "$designs");;
esac
show() {
    local -a diagnostic=()
    local arg lower hide_next=0
    for arg in "${argv[@]}"; do
        lower=${arg,,}
        if (( hide_next )); then diagnostic+=('[REDACTED]'); hide_next=0
        elif [[ $lower == *token* || $lower == *password* || $lower == *vnc_pw* ]]; then
            if [[ $arg == *=* ]]; then diagnostic+=("${arg%%=*}=[REDACTED]")
            else diagnostic+=("$arg"); hide_next=1; fi
        else diagnostic+=("$arg"); fi
    done
    if (( json )); then python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "${diagnostic[@]}"
    else printf '%q ' "${diagnostic[@]}"; printf '\n'; fi
}
if [[ ${DRY_RUN:-0} == 1 || $mode == print ]]; then show; exit 0; fi
if [[ $mode == pull ]]; then
    [[ -z ${NO_PULL:-} ]] || exit 0
    docker image inspect "$reference" >/dev/null 2>&1 && exit 0
    exec "${argv[@]}"
fi
if [[ $mode == build || $mode == push || $mode == rm || $mode == devcontainer ]]; then exec "${argv[@]}"; fi
# Exact-name lookup, not substring filters. Never delete/recreate automatically.
existing=$(docker container ls -a --format '{{.Names}}')
if printf '%s\n' "$existing" | python3 -c 'import sys; sys.exit(0 if sys.argv[1] in sys.stdin.read().splitlines() else 1)' "$name"; then
    state=$(docker container inspect "$name")
    decision=$(python3 -c 'import json,sys; c=json.load(sys.stdin)[0]; mounts=c.get("Mounts",[]); ok=c["Config"]["Image"]==sys.argv[1] and any(m.get("Source")==sys.argv[2] and m.get("Destination")=="/home/designer/shared" for m in mounts); print("running" if c["State"]["Running"] else "same" if ok else "different")' "$reference" "$designs" <<< "$state")
    if [[ $decision == running ]]; then
        echo "Container is running; use: docker exec -it $name /bin/bash" >&2; exit 2
    elif [[ $decision == different || $mode != attach ]]; then
        echo 'Container exists; explicitly remove it to recreate, or use make attach for compatible stopped containers.' >&2; exit 2
    fi
    exec docker container start -ai "$name"
fi
if [[ -z ${NO_PULL:-} ]] && ! docker image inspect "$reference" >/dev/null 2>&1; then
    docker image pull "$reference"
fi
mkdir -p -- "$designs"
if [[ $mode == test ]]; then
    mkdir -p -- "$root/tests/run"
    docker image inspect --format '{{.Id}}' "$reference" > "$root/tests/run/image-id.txt"
    printf '%s\n' "$reference" > "$root/tests/run/image-reference.txt"
    printf 'Testing image %s (%s)\n' "$reference" "$(< "$root/tests/run/image-id.txt")"
fi
exec "${argv[@]}"
