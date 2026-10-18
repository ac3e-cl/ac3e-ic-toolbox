#!/usr/bin/env bash
# Source this helper, then call configure_buildkit before invoking BUILD_COMMAND.
configure_buildkit() {
    BUILD_COMMAND=(docker build)
    case ${BUILD_OUTPUT:-local} in
        local) ;;
        registry)
            if [[ -z ${BUILD_BUILDER:-} || -z ${BUILD_METADATA_FILE:-} ]]; then
                echo 'Registry output requires BUILD_BUILDER and BUILD_METADATA_FILE.' >&2
                return 2
            fi
            ;;
        *) echo 'BUILD_OUTPUT must be local or registry.' >&2; return 2 ;;
    esac
    [[ -n ${BUILD_MAX_PARALLELISM:-}${BUILD_BUILDER:-} ]] || return 0
    local parallelism=${BUILD_MAX_PARALLELISM:-2}
    local builder=${BUILD_BUILDER:-ac3e-ic-toolbox-p${parallelism}}
    local inspection config status
    if [[ ! $parallelism =~ ^[1-9][0-9]*$ ]]; then
        echo 'BUILD_MAX_PARALLELISM must be a positive integer.' >&2
        return 2
    fi
    if [[ ! $builder =~ ^[A-Za-z][A-Za-z0-9_.-]*$ || $builder == default ]]; then
        echo 'BUILD_BUILDER must be a non-default Buildx builder name.' >&2
        return 2
    fi
    docker buildx version >/dev/null || return
    if inspection=$(docker buildx inspect "$builder" 2>/dev/null); then
        # Never mutate or replace an existing builder: its cache may be valuable.
        if ! grep -Eq '^Driver:[[:space:]]+docker-container[[:space:]]*$' <<< "$inspection" ||
           ! grep -Eq "max-parallelism[[:space:]]*=[[:space:]]*${parallelism}([^0-9]|$)" <<< "$inspection"; then
            echo "Builder $builder does not advertise docker-container with max-parallelism=$parallelism; choose another BUILD_BUILDER (existing builder left untouched)." >&2
            return 2
        fi
    else
        config=$(mktemp "${TMPDIR:-/tmp}/ac3e-buildkit.XXXXXX") || return
        printf '[worker.oci]\n  max-parallelism = %s\n' "$parallelism" > "$config"
        # Do not --use: the user's selected builder and normal cache stay intact.
        if docker buildx create --name "$builder" --driver docker-container --buildkitd-config "$config" >/dev/null; then
            status=0
        else
            status=$?
        fi
        rm -f -- "$config"
        (( status == 0 )) || return "$status"
    fi
    BUILD_COMMAND=(docker buildx build --builder "$builder" --load)
    if [[ ${BUILD_OUTPUT:-local} == registry ]]; then
        # Stream compressed layers to the registry, never through Docker's loader.
        BUILD_COMMAND=(docker buildx build --builder "$builder"
            --output type=registry,compression=gzip,compression-level=1
            --metadata-file "$BUILD_METADATA_FILE")
    fi
}
