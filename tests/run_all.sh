#!/usr/bin/env bash
# Run the mounted integration tests directly inside the EDA container.
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
mode=regular
if [[ $# == 1 && $1 == --long-only ]]; then
    mode=long
elif [[ $# != 0 ]]; then
    printf 'Usage: %s [--long-only]\n' "$0" >&2; exit 2
fi
cd "$TEST_ROOT"
output="$TEST_ROOT/run"
[[ $mode != long ]] || output="$output/full"
mkdir -p "$output/logs"
summary="$output/summary.tsv"
printf 'test\tstatus\tseconds\tlog\n' > "$summary"
passed=0
failed=0
excluded=0
declare -A exclusions=()
if [[ -f "$TEST_ROOT/exclusions.json" ]]; then
    exclusion_rows=$(python3 - "$TEST_ROOT/exclusions.json" "$mode" <<'PY'
import json
import sys
with open(sys.argv[1]) as stream:
    data = json.load(stream)
exclusions = dict(data.get('tests', {}))
if sys.argv[2] == 'regular':
    exclusions = {**data.get('long_running', {}), **exclusions}
for name, reason in exclusions.items():
    assert '\t' not in name + reason and '\n' not in name + reason
    print(name + '\t' + reason)
PY
)
    while IFS=$'\t' read -r name reason; do
        [[ -z $name ]] || exclusions["$name"]=$reason
    done <<< "$exclusion_rows"
fi
mapfile -t tests < <(find analog digital gui inventory pdk -type f -name '*.sh' 2>/dev/null | LC_ALL=C sort)
if [[ $mode == long ]]; then
    long_rows=$(python3 - "$TEST_ROOT/exclusions.json" <<'PY'
import json, sys
with open(sys.argv[1]) as stream:
    print('\n'.join(sorted(json.load(stream).get('long_running', {}))))
PY
)
    tests=()
    while IFS= read -r test; do
        [[ -z $test ]] || tests+=("$test")
    done <<< "$long_rows"
fi
[[ ${#tests[@]} -gt 0 ]] || { echo 'No integration tests discovered' >&2; exit 1; }
for test in "${tests[@]}"; do
    log="$output/logs/${test//\//_}.log"
    printf '\nRunning %s\n' "$test"
    if [[ -v exclusions["$test"] ]]; then
        excluded=$((excluded + 1))
        printf '%s\n' "${exclusions[$test]}" > "$log"
        printf '%s\tEXCLUDED\t0\t%s\n' "$test" "$log" >> "$summary"
        printf '%s: EXCLUDED — %s\n' "$test" "${exclusions[$test]}"
        continue
    fi
    start=$SECONDS
    status=PASS
    default_timeout=900
    case "$test" in pdk/librelane-template-*.sh) default_timeout=14400 ;; esac
    if timeout --kill-after=10 "${TEST_TIMEOUT:-$default_timeout}" bash "$TEST_ROOT/$test" > "$log" 2>&1; then
        passed=$((passed + 1))
    else
        code=$?
        status=FAIL
        failed=$((failed + 1))
        printf 'Exit status: %s\n' "$code" >> "$log"
        cat "$log" >&2
    fi
    elapsed=$((SECONDS - start))
    printf '%s\t%s\t%s\t%s\n' "$test" "$status" "$elapsed" "$log" >> "$summary"
    printf '%s: %s (%ss)\n' "$test" "$status" "$elapsed"
done
printf '\nFinal summary\n'
while IFS=$'\t' read -r test status elapsed log; do
    [[ $test == test ]] && continue
    printf '  %-45s %-8s %ss\n' "$test" "$status" "$elapsed"
done < "$summary"
printf '\nSummary: %s passed, %s failed, %s excluded, %s total\n' "$passed" "$failed" "$excluded" "${#tests[@]}"
if [[ -f "$TEST_ROOT/exclusions.json" ]]; then
    python3 - "$TEST_ROOT/exclusions.json" <<'PY'
import json
import sys
with open(sys.argv[1]) as stream:
    exclusions = json.load(stream)
for name, reason in exclusions.get('manifest', {}).items():
    print(f'Inventory exclusion: {name} — {reason}')
PY
fi
printf 'Logs and summary: %s/\n' "$output"
[[ $failed == 0 ]]
