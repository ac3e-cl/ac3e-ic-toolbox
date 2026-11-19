#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
windows=0
case $(uname -s) in
    MINGW*|MSYS*|CYGWIN*) windows=1; root=$(cygpath -am -- "$root");;
esac
docker_env=()
if (( windows )); then docker_env=(env MSYS_NO_PATHCONV=1 MSYS2_ARG_CONV_EXCL='*'); fi
# Scope conversion protection to Docker, never to Python/PowerShell helpers.
docker() { command "${docker_env[@]}" docker "$@"; }
docker_exec() { exec "${docker_env[@]}" docker "$@"; }
execute_argv() {
    if [[ ${argv[0]} == docker ]]; then docker_exec "${argv[@]:1}"
    else exec "${argv[@]}"; fi
}
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
configure_shared=0
case $mode in
    shell|x|vnc|jupyter)
        if [[ ${DRY_RUN:-0} != 1 ]]; then
            # Keep other local settings intact, including files without a final newline.
            [[ -e $env_file ]] || (umask 077; touch -- "$env_file")
            if [[ -z ${DESIGNS:-} && -z ${SHARED_DIR:-} && -t 0 ]]; then
                printf 'Choose your development directory.\nIt will be mounted at /home/designer/shared inside the container.\nDevelopment directory [%s]: ' "$root/shared" >&2
                IFS= read -r selected || { echo 'Directory selection cancelled.' >&2; exit 2; }
                SHARED_DIR=${selected:-$root/shared}
                # Expand a leading home shortcut without evaluating shell code.
                if [[ $SHARED_DIR == '~' ]]; then SHARED_DIR=$HOME
                elif [[ $SHARED_DIR == '~/'* ]]; then SHARED_DIR=$HOME/${SHARED_DIR:2}; fi
                configure_shared=1
            fi
        fi;;
esac
designs=${DESIGNS:-${SHARED_DIR:-$root/shared}}
if (( windows )); then designs=$(cygpath -am -- "$designs")
else [[ $designs == /* ]] || designs=$PWD/$designs; fi
[[ $designs != *,* ]] || { echo 'Docker bind paths cannot contain commas' >&2; exit 2; }
if (( configure_shared )); then
    [[ $designs != *$'\n'* && $designs != *$'\r'* ]] || { echo 'Directory paths cannot contain line breaks' >&2; exit 2; }
    if [[ ! -d $designs ]]; then
        mkdir -p -- "$designs"
        printf 'The directory did not exist; created an empty directory: %s\n' "$designs" >&2
    fi
    [[ -r $designs && -w $designs && -x $designs ]] || { echo 'Development directory is not accessible and writable' >&2; exit 2; }
    # Last assignment wins on future loads; replace an empty setting rather than
    # appending a duplicate that the literal loader would ignore.
    python3 - "$env_file" "$designs" <<'PY'
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
lines = path.read_text().splitlines(keepends=True)
lines = [line for line in lines if not line.startswith('SHARED_DIR=')]
text = ''.join(lines)
if text and not text.endswith('\n'):
    text += '\n'
with path.open('w') as stream:
    stream.write(text + 'SHARED_DIR=' + sys.argv[2] + '\n')
PY
fi
default_uid=$(id -u); default_gid=$(id -g)
if (( windows )); then default_uid=1000; default_gid=1000; fi
uid=${CONTAINER_USER:-${USER_ID:-$default_uid}}
gid=${CONTAINER_GROUP:-${USER_GROUP:-$default_gid}}
[[ -z ${ROOT:-} ]] || { uid=0; gid=0; }
[[ $uid =~ ^[0-9]+$ && $gid =~ ^[0-9]+$ ]] || { echo 'UID/GID must be numeric' >&2; exit 2; }
project=$(jq -r .image.name "$root/manifest.json")
name=${CONTAINER_NAME:-$project}
# Integration runs are disposable and must never replace the user's container.
[[ $mode != test ]] || name=${CONTAINER_NAME:-$project-test-$$}

argv=(docker run --pull=never --name "$name" --user "$uid:$gid" --mount "type=bind,source=$designs,target=/home/designer/shared" --mount "type=bind,source=$root/tests,target=/home/designer/tests" --env SHELL=/bin/bash --env "PDK=${PDK:-ihp-sg13g2}")
session_mode=$mode
[[ $mode != attach ]] || session_mode=x
argv+=(--label "org.ac3e.ic-toolbox.mode=$session_mode")
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
        xserver=${AC3E_XSERVER:-auto}
        if [[ $xserver == auto ]]; then
            xserver=native
            # Preserve WSLg; other WSL sessions use the Windows VcXsrv route.
            if (( windows )); then
                xserver=vcxsrv
                # MSYS terminals may inherit another X server's dynamic display.
                # Managed VcXsrv always uses display 0; native mode is the opt-out.
                export DISPLAY=host.docker.internal:0
            elif [[ -n ${WSL_INTEROP:-} && -z ${WAYLAND_DISPLAY:-} ]]; then
                xserver=vcxsrv
            fi
        fi
        case $xserver in
            vcxsrv)
                case ${DISPLAY:-} in
                    ''|:*|unix:*) export DISPLAY=host.docker.internal:0 ;;
                esac
                export DISPLAY
                argv+=(--env "LIBGL_ALWAYS_INDIRECT=${LIBGL_ALWAYS_INDIRECT:-1}")
                if [[ ${DRY_RUN:-0} != 1 ]]; then
                    if (( windows )) && [[ -n ${XAUTHORITY:-} ]]; then
                        export XAUTHORITY=$(cygpath -am -- "$XAUTHORITY")
                    fi
                    XAUTHORITY=$(python3 "$root/runtime/vcxsrv.py")
                    if (( windows )); then XAUTHORITY=${XAUTHORITY%$'\r'}; fi
                fi
                ;;
            native) ;;
            *) echo 'AC3E_XSERVER must be auto, native or vcxsrv' >&2; exit 2 ;;
        esac
        [[ -n ${DISPLAY:-} ]] || { echo 'X mode requires DISPLAY' >&2; exit 2; }
        argv+=(--env "DISPLAY=$DISPLAY")
        if [[ $DISPLAY == :* || $DISPLAY == unix:* ]]; then
            argv+=(--mount type=bind,source=/tmp/.X11-unix,target=/tmp/.X11-unix,readonly)
        fi
        auth=${XAUTHORITY:-$HOME/.Xauthority}
        if (( windows )); then auth=$(cygpath -am -- "$auth"); fi
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
argv+=(--tmpfs "/tmp/ac3e-ic-toolbox-home:rw,nosuid,nodev,mode=0700,uid=$uid,gid=$gid" --env HOME=/tmp/ac3e-ic-toolbox-home --entrypoint /bin/bash)
argv+=("$reference" --noprofile --norc -c "$bootstrap" ac3e-ic-toolbox-home)
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
    if (( json )); then printf '%s\0' "${diagnostic[@]}" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.buffer.read().decode().split("\0")[:-1]))'
    else printf '%q ' "${diagnostic[@]}"; printf '\n'; fi
}
if [[ ${DRY_RUN:-0} == 1 || $mode == print ]]; then show; exit 0; fi
if [[ $mode == pull ]]; then
    [[ -z ${NO_PULL:-} ]] || exit 0
    docker image inspect "$reference" >/dev/null 2>&1 && exit 0
    execute_argv
fi
if [[ $mode == build || $mode == push || $mode == rm || $mode == devcontainer ]]; then execute_argv; fi
# Exact-name lookup. Replacements require consent and an available target image.
image_ready=0
existing=$(docker container ls -a --format '{{.Names}}')
if printf '%s\n' "$existing" | python3 -c 'import sys; sys.exit(0 if sys.argv[1] in sys.stdin.read().splitlines() else 1)' "$name"; then
    state=$(docker container inspect "$name")
    # A failed Windows create can retain converted entrypoint/bind arguments.
    # Never offer this shortcut for a container that has ever been started.
    if (( windows )) && [[ $mode != test ]] && jq -e '.[0].State |
        .Status == "created" and .Running == false and
        (.StartedAt | startswith("0001-01-01T00:00:00")) and
        ((.Error // "") | length > 0)' <<< "$state" >/dev/null; then
        printf 'Container %s failed during creation and never started.\n' "$name" >&2
        if [[ ! -t 0 ]]; then
            printf 'Run the launcher interactively to confirm recreation, or inspect and explicitly remove it:\n  docker container inspect %q\n  docker container rm %q\nThen rerun the launcher. Removal discards internal files; mounted designs are preserved.\n' "$name" "$name" >&2
            exit 2
        fi
        printf 'Recreate it with the corrected Windows settings? This removes internal files; mounted designs are preserved. [y/N]: ' >&2
        IFS= read -r answer || answer=
        case $answer in y|Y|yes|YES) ;; *) echo 'Container kept unchanged.' >&2; exit 0;; esac
        # Resolve the image and bind directory before removing anything. No force.
        if ! docker image inspect "$reference" >/dev/null 2>&1; then
            [[ -z ${NO_PULL:-} ]] || { echo 'Requested image is missing and NO_PULL is set.' >&2; exit 2; }
            docker image pull "$reference"
        fi
        mkdir -p -- "$designs"
        docker container rm "$name"
        execute_argv
    fi
    if (( windows )); then
        # Docker Desktop may report native paths or its VM's host-mount prefix.
        state=$(python3 -c '
import json, ntpath, re, sys
state = json.load(sys.stdin)
def canonical(path):
    path = path.replace("\\", "/")
    for prefix in ("/run/desktop/mnt/host", "/host_mnt", "/mnt/host"):
        if path.startswith(prefix + "/"):
            path = path[len(prefix):]
            break
    path = re.sub(r"^/([a-zA-Z])(?=/)", r"\1:", path)
    return ntpath.normcase(ntpath.normpath(path))
for mount in state[0].get("Mounts", []):
    for expected in sys.argv[1:]:
        if expected and canonical(mount.get("Source", "")) == canonical(expected):
            mount["Source"] = expected
print(json.dumps(state))
' "$designs" "${auth:-}" <<< "$state")
    fi
    metadata=$(python3 -c 'import json,sys; c=json.load(sys.stdin)[0]; print(c["Config"]["Image"]); print(int(c["State"]["Running"])); print(int(any(m.get("Source")==sys.argv[1] and m.get("Destination")=="/home/designer/shared" for m in c.get("Mounts",[]))))' "$designs" <<< "$state")
    if (( windows )); then metadata=${metadata//$'\r'/}; fi
    mapfile -t fields <<< "$metadata"
    current_reference=${fields[0]}
    running=${fields[1]}
    if [[ $mode == x && $current_reference == "$reference" ]]; then
        expected_gl= expected_auth=
        [[ $xserver != vcxsrv ]] || expected_gl=${LIBGL_ALWAYS_INDIRECT:-1}
        [[ ! -f $auth ]] || expected_auth=$auth
        if ! jq -e --arg display "$DISPLAY" --arg gl "$expected_gl" --arg auth "$expected_auth" '
            .[0] |
            any(.Config.Env[]?; . == ("DISPLAY=" + $display)) and
            ($gl == "" or any(.Config.Env[]?; . == ("LIBGL_ALWAYS_INDIRECT=" + $gl))) and
            ($auth == "" or any(.Mounts[]?; .Source == $auth and .Destination == "/tmp/.Xauthority"))
        ' <<< "$state" >/dev/null; then
            echo 'X11 configuration changed; explicitly recreate the container to apply the display, authorization or rendering settings.' >&2
            exit 2
        fi
    fi
    stored_mode=$(jq -r '.[0].Config.Labels["org.ac3e.ic-toolbox.mode"] // empty' <<< "$state")
    if [[ -n $stored_mode && $stored_mode != "$session_mode" && $mode != attach && ! ( $session_mode == shell && $stored_mode == x ) ]]; then
        printf 'Container %s uses %s mode; remove it explicitly before switching to %s.\n' "$name" "$stored_mode" "$session_mode" >&2
        exit 2
    fi
    if [[ $mode == x && -z $stored_mode ]] && ! jq -e '.[0] | any(.Config.Env[]?; startswith("DISPLAY=") and . != "DISPLAY=") and any(.Mounts[]?; .Destination == "/tmp/.X11-unix")' <<< "$state" >/dev/null; then
        echo 'Container lacks X11 configuration; explicitly remove it before using make start.' >&2
        exit 2
    fi
    if [[ ${fields[2]} != 1 || $mode == test ]]; then
        echo 'Container exists with incompatible configuration or test mode; explicitly remove it to recreate.' >&2; exit 2
    fi
    replace=0
    refresh=0
    update_reason=
    if [[ $current_reference != "$reference" ]]; then
        update_reason="from $current_reference to $reference"
    elif [[ -t 0 && -z ${NO_PULL:-} ]]; then
        local_image=$(docker image inspect "$reference" 2>/dev/null || printf '[]')
        local_id=$(jq -r '.[0].Id // empty' <<< "$local_image")
        container_id=$(jq -r '.[0].Image // empty' <<< "$state")
        if [[ -n $local_id && -n $container_id && $local_id != "$container_id" ]]; then
            update_reason="to the locally installed image for $reference"
        elif [[ $(jq '.[0].RepoDigests // [] | length' <<< "$local_image") -gt 0 ]]; then
            # Metadata only; never download layers before the user agrees.
            if remote_manifest=$(timeout 10 "${docker_env[@]}" docker buildx imagetools inspect "$reference" --format '{{json .Manifest}}' 2>/dev/null); then
                remote_digest=$(jq -r '.digest // empty' <<< "$remote_manifest")
                if [[ -n $remote_digest ]] && ! jq -e --arg digest "$remote_digest" '.[0].RepoDigests // [] | any(endswith("@" + $digest))' <<< "$local_image" >/dev/null; then
                    update_reason="to the published update for $reference"
                    refresh=1
                fi
            else
                echo 'Update check unavailable; keeping the installed image.' >&2
            fi
        fi
    fi
    if [[ -n $update_reason ]]; then
        if [[ ! -t 0 ]]; then
            printf 'Container %s uses %s; requested %s. Run interactively to confirm replacement.\n' "$name" "$current_reference" "$reference" >&2
            exit 2
        fi
        printf 'Update %s %s?\nThis removes its internal files and stops its processes; mounted designs are preserved. [y/N]: ' "$name" "$update_reason" >&2
        IFS= read -r answer || answer=
        case $answer in y|Y|yes|YES) replace=1;; *) echo 'Container kept unchanged.' >&2; exit 0;; esac
    fi
    if (( replace )); then
        # Pull before stopping/removing anything: failure leaves the old session intact.
        if (( refresh )) || ! docker image inspect "$reference" >/dev/null 2>&1; then
            [[ -z ${NO_PULL:-} ]] || { echo 'Requested image is missing and NO_PULL is set.' >&2; exit 2; }
            docker image pull "$reference"
        fi
        image_ready=1
        if [[ $running == 1 ]]; then docker container stop "$name"; fi
        docker container rm "$name"
    else
        if [[ $running == 1 ]]; then
            case $mode in
                shell|x|attach) if (( $# )); then docker_exec exec -it "$name" "$@"; else docker_exec exec -it "$name" /bin/bash; fi;;
                vnc|jupyter) printf 'Container %s is already running.\n' "$name"; exit 0;;
            esac
        fi
        case $mode in
            shell|x|attach) docker_exec container start -ai "$name";;
            vnc|jupyter) docker_exec container start "$name";;
        esac
    fi
fi
if [[ $image_ready == 0 && -z ${NO_PULL:-} ]] && ! docker image inspect "$reference" >/dev/null 2>&1; then
    docker image pull "$reference"
fi
mkdir -p -- "$designs"
if [[ $mode == test ]]; then
    mkdir -p -- "$root/tests/run"
    docker image inspect --format '{{.Id}}' "$reference" > "$root/tests/run/image-id.txt"
    printf '%s\n' "$reference" > "$root/tests/run/image-reference.txt"
    printf 'Testing image %s (%s)\n' "$reference" "$(< "$root/tests/run/image-id.txt")"
fi
execute_argv
