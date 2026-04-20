#!/usr/bin/env bash
# Post-deploy smoke tests for the Order Portal.
# Usage:
#   scripts/verify_order_portal.sh               # prod
#   BASE=http://localhost:8080 scripts/verify_order_portal.sh    # local

set -u
BASE="${BASE:-https://salesheet.leka.studio}"
PASS=0; FAIL=0

check() {
  local name="$1"; local cmd="$2"; local expect="$3"
  local got
  got="$(eval "${cmd}" 2>&1 | head -1)"
  if [[ "${got}" == *"${expect}"* ]]; then
    echo "  ✓ ${name}  ->  ${got}"
    PASS=$((PASS + 1))
  else
    echo "  ✗ ${name}  -> got '${got}', expected to contain '${expect}'"
    FAIL=$((FAIL + 1))
  fi
}

echo "==> Regression check: legacy public pages"
check "Landing page"        "curl -sI ${BASE}/"                "200"
check "WPC Fence"           "curl -sI ${BASE}/wpc-fence/"      "200"
check "WPC Profile"         "curl -sI ${BASE}/wpc-profile/"    "200"
check "Health"              "curl -s ${BASE}/_healthz"          "ok"

echo ""
echo "==> Auth gate"
check "/auth/login renders"           "curl -sI ${BASE}/auth/login"            "200"
check "/order/new → redirect"         "curl -sI ${BASE}/order/new"             "302"
check "/admin/orders → redirect"      "curl -sI ${BASE}/admin/orders"          "302"
check "/api/order/catalog → 401"      "curl -sI ${BASE}/api/order/catalog"     "401"

echo ""
echo "==> Legacy /api/quote still works"
check "Legacy /api/quote (generic)" \
  "curl -s -X POST ${BASE}/api/quote -H 'Content-Type: application/json' -d '{\"name\":\"Test\",\"email\":\"t@t.com\",\"message\":\"Hello world test message ten chars\"}'" \
  '"ok":true'

echo ""
echo "==> Totals: ${PASS} passed, ${FAIL} failed"
if [[ ${FAIL} -gt 0 ]]; then exit 1; fi
echo "    All smoke checks passed. Remember to manually test the auth flow in a browser."
