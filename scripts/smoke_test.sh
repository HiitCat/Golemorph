#!/usr/bin/env bash
# Smoke test: exercise every golemorph CLI behaviour and show how it responds.
# Not a unit test (that is `pytest tests/`) - a human-readable tour that also
# fails loudly if a command exits unexpectedly.
#
# Usage:  bash scripts/smoke_test.sh
set -u

# Run from the repo root so `python3 -m golemorph` finds the package.
cd "$(dirname "$0")/.." || exit 1
GM=(python3 -m golemorph)

pass=0 fail=0

hdr() { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }

# ok "<label>" <cmd...>   -> command must succeed (exit 0)
ok() {
    local label=$1; shift
    printf '\033[2m$ %s\033[0m\n' "$*"
    if "$@"; then
        pass=$((pass + 1))
    else
        fail=$((fail + 1))
        printf '\033[1;31m  ! expected success, got exit %d\033[0m\n' "$?"
    fi
}

# fails "<label>" <cmd...> -> command must FAIL (non-zero), for error paths
fails() {
    local label=$1; shift
    printf '\033[2m$ %s\033[0m\n' "$*"
    if "$@" 2>&1; then
        fail=$((fail + 1))
        printf '\033[1;31m  ! expected failure, but it succeeded\033[0m\n'
    else
        pass=$((pass + 1))
        printf '\033[2m  (failed as expected)\033[0m\n'
    fi
}

hdr "Origins listing"
ok "list" "${GM[@]}" --list-origins

hdr "Default invocation (no args -> one USA name)"
ok "default" "${GM[@]}"

hdr "Output formats"
for fmt in name csv json gophish; do
    ok "$fmt" "${GM[@]}" -o FRA -n 3 --seed 1 -f "$fmt"
done

hdr "Gender forcing"
ok "male"   "${GM[@]}" -o DEU -n 3 --seed 1 -g Male
ok "female" "${GM[@]}" -o DEU -n 3 --seed 1 -g Female

hdr "Unique modes"
ok "unique full (bare)" "${GM[@]}" -o USA -n 10 --seed 1 --unique
ok "unique first"       "${GM[@]}" -o USA -n 10 --seed 1 --unique first
ok "unique last"        "${GM[@]}" -o USA -n 10 --seed 1 --unique last

hdr "Weighting"
ok "weighted (default)" "${GM[@]}" -o ITA -n 3 --seed 1
ok "unweighted"         "${GM[@]}" -o ITA -n 3 --seed 1 --unweighted

hdr "Case-insensitive origin"
ok "lowercase -o chn" "${GM[@]}" -o chn -n 2 --seed 1

hdr "Reproducibility (same seed -> identical output)"
a=$("${GM[@]}" -o RUS -n 5 --seed 42)
b=$("${GM[@]}" -o RUS -n 5 --seed 42)
if [ "$a" = "$b" ]; then
    printf '\033[2m  identical ✓\033[0m\n'; pass=$((pass + 1))
else
    printf '\033[1;31m  ! seed not reproducible\033[0m\n'; fail=$((fail + 1))
fi

hdr "Write to file"
tmp=$(mktemp)
ok "gophish -> file" "${GM[@]}" -o FRA -n 5 --seed 1 -f gophish --output "$tmp"
printf '\033[2m  wrote %s lines\033[0m\n' "$(wc -l < "$tmp")"
rm -f "$tmp"

hdr "Every origin loads (one persona each, full record)"
for code in $("${GM[@]}" --list-origins | cut -f1); do
    if ! out=$("${GM[@]}" -o "$code" -n 1 --seed 1 -f json 2>&1); then
        printf '\033[1;31m  ! %s failed: %s\033[0m\n' "$code" "$out"
        fail=$((fail + 1))
    else
        pass=$((pass + 1))
    fi
done
printf '\033[2m  %d origins generated\033[0m\n' \
    "$("${GM[@]}" --list-origins | wc -l)"

hdr "Error paths (must fail cleanly, no traceback)"
fails "unknown origin"       "${GM[@]}" -o ZZZ
fails "unique pool too small" "${GM[@]}" -o KOR -n 100000 --unique first
fails "bad gender"           "${GM[@]}" -g Other
fails "bad unique mode"      "${GM[@]}" --unique middle
fails "bad format"           "${GM[@]}" -f yaml

hdr "Summary"
printf 'passed: \033[1;32m%d\033[0m   failed: \033[1;31m%d\033[0m\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
