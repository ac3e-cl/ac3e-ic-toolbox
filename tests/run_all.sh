#!/usr/bin/env bash
# Run the mounted integration tests directly inside the EDA container.
set -euo pipefail
TEST_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
[[ $# == 0 ]] || { printf 'Usage: %s\n' "$0" >&2; exit 2; }
cd "$TEST_ROOT"
mkdir -p run/logs
summary="$TEST_ROOT/run/summary.tsv"
printf 'test\tstatus\tseconds\tlog\n' > "$summary"
passed=0
failed=0
excluded=0
declare -A exclusions=()
if [[ -f "$TEST_ROOT/exclusions.json" ]]; then
    exclusion_rows=$(python3 - "$TEST_ROOT/exclusions.json" <<'PY'
import json
import sys
with open(sys.argv[1]) as stream:
    data = json.load(stream)
for name, reason in data.get('tests', {}).items():
    assert '\t' not in name + reason and '\n' not in name + reason
    print(name + '\t' + reason)
PY
)
    while IFS=$'\t' read -r name reason; do
        [[ -z $name ]] || exclusions["$name"]=$reason
    done <<< "$exclusion_rows"
fi
mapfile -t tests < <(find analog digital gui inventory pdk -type f -name '*.sh' 2>/dev/null | LC_ALL=C sort)
[[ ${#tests[@]} -gt 0 ]] || { echo 'No integration tests discovered' >&2; exit 1; }
for test in "${tests[@]}"; do
    log="$TEST_ROOT/run/logs/${test//\//_}.log"
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
    if timeout --kill-after=10 "${TEST_TIMEOUT:-900}" bash "$TEST_ROOT/$test" > "$log" 2>&1; then
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
printf 'Logs and summary: %s/run/\n' "$TEST_ROOT"
[[ $failed == 0 ]]
