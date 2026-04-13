#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://localhost:8080}"
API="${BASE}/api/v2"
PASS=0
FAIL=0

check() {
    local name="$1"
    local url="$2"
    local expected="${3:-200}"
    local method="${4:-GET}"
    local data="${5:-}"

    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        local csrf_header=()
        if [ -n "${CSRF:-}" ]; then
            csrf_header=(-H "X-CSRFToken: $CSRF" -b "$COOKIE_JAR")
        fi
        code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" "${csrf_header[@]}" -d "$data" "$url" 2>/dev/null || echo "000")
    else
        code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    fi

    if [ "$code" = "$expected" ]; then
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name (expected $expected, got $code)"
        FAIL=$((FAIL + 1))
    fi
}

check "health" "$BASE/health/"
check "readiness" "$BASE/ready/"
check "api_root" "$API/"
COOKIE_JAR=$(mktemp)
trap 'rm -f "$COOKIE_JAR"' EXIT

curl -s -c "$COOKIE_JAR" "$API/auth/csrf/" >/dev/null 2>&1 || true
CSRF=$(awk '$6 == "csrftoken" {print $7}' "$COOKIE_JAR" | tail -n 1)

check "login" "$API/auth/login/" "200" "POST" '{"username":"public_user","password":"PublicPass123!"}'

curl -s -c "$COOKIE_JAR" -b "$COOKIE_JAR" -X POST \
    -H "Content-Type: application/json" \
    -H "X-CSRFToken: $CSRF" \
    -d '{"username":"public_user","password":"PublicPass123!"}' \
    "$API/auth/login/" >/dev/null 2>&1

SESSION=$(awk '$6 == "sessionid" {print $7}' "$COOKIE_JAR" | tail -n 1)

if [ -n "$SESSION" ]; then
    PASS=$((PASS + 1))
else
    echo "FAIL: session"
    FAIL=$((FAIL + 1))
fi

AUTH="-b $COOKIE_JAR"

for ep in tickets incidents assets comments report-jobs webhook-configs audit-events users; do
    code=$(curl -s -o /dev/null -w "%{http_code}" $AUTH "$API/$ep/" 2>/dev/null || echo "000")
    if [ "$code" = "200" ]; then PASS=$((PASS+1)); else echo "FAIL: $ep ($code)"; FAIL=$((FAIL+1)); fi
done

code=$(curl -s -o /dev/null -w "%{http_code}" $AUTH -X POST -H "Content-Type: application/json" -H "X-CSRFToken: $CSRF" \
    -d '{"title":"test","description":"test","priority":"low"}' \
    "$API/tickets/" 2>/dev/null || echo "000")
if [ "$code" = "201" ]; then PASS=$((PASS+1)); else echo "FAIL: create_ticket ($code)"; FAIL=$((FAIL+1)); fi

check "legacy_api" "$BASE/api/v1/"
check "legacy_tickets" "$BASE/api/v1/tickets"
check "legacy_assets" "$BASE/api/v1/assets"

echo "$PASS passed, $FAIL failed"
if [ $FAIL -gt 0 ]; then exit 1; fi
