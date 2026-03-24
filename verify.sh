#!/bin/bash
# verify.sh — GO Corporation Post-Build Verification
# Usage: ./verify.sh [--ci-mode] [--verbose]
# Outputs: verify-report.json (machine-readable) + verify-report.txt (human-readable)

set -e

CI_MODE=false
VERBOSE=false
PASS=0
FAIL=0
WARN=0
REPORT_JSON="verify-report.json"
REPORT_TXT="verify-report.txt"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Parse flags
for arg in "$@"; do
  case $arg in
    --ci-mode) CI_MODE=true ;;
    --verbose) VERBOSE=true ;;
  esac
done

echo "=== GO Corporation Build Verification ==="
echo "Started: $TIMESTAMP"
echo ""

# Load manifest
MANIFEST="manifest.json"
if [ ! -f "$MANIFEST" ]; then
  echo "[WARN] manifest.json not found — using environment variables"
  WARN=$((WARN+1))
fi

# Helper functions
pass() { echo "[PASS] $1"; PASS=$((PASS+1)); }
fail() { echo "[FAIL] $1"; FAIL=$((FAIL+1)); }
warn() { echo "[WARN] $1"; WARN=$((WARN+1)); }

# =============================================
# 1. ENVIRONMENT CHECKS
# =============================================
echo "--- 1. Environment Checks ---"

[ -f "manifest.example.json" ] && pass "manifest.example.json exists" || fail "manifest.example.json missing"
[ -f "CHANGELOG.md" ] && pass "CHANGELOG.md exists" || fail "CHANGELOG.md missing"
[ -f "cloudbuild.yaml" ] && pass "cloudbuild.yaml exists" || fail "cloudbuild.yaml missing"
[ -f "CLAUDE.md" ] && pass "CLAUDE.md exists" || warn "CLAUDE.md missing (recommended)"

# =============================================
# 2. PEAK API CONNECTIVITY
# =============================================
echo ""
echo "--- 2. Peak API Connectivity ---"

PEAK_BASE="https://api.peakaccount.com/api/v1"
PEAK_TOKEN="${PEAK_API_TOKEN:-}"

if [ -n "$PEAK_TOKEN" ]; then
  PEAK_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer $PEAK_TOKEN" \
    "$PEAK_BASE/contacts?code=C00001")
  [ "$PEAK_STATUS" = "200" ] && pass "Peak API — contacts endpoint (C00001)" || fail "Peak API — HTTP $PEAK_STATUS"
else
  warn "PEAK_API_TOKEN not set — skipping Peak API tests"
fi

# =============================================
# 3. N8N CONNECTIVITY
# =============================================
echo ""
echo "--- 3. n8n Connectivity ---"

N8N_BASE="${N8N_BASE_URL:-https://gocorp.app.n8n.cloud}"
N8N_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$N8N_BASE/healthz" 2>/dev/null || echo "000")
[ "$N8N_STATUS" = "200" ] && pass "n8n health check" || warn "n8n health check — HTTP $N8N_STATUS (may need auth)"

# =============================================
# 4. GCP CLOUD RUN (if deployed)
# =============================================
echo ""
echo "--- 4. GCP Cloud Run ---"

SERVICE_URL="${CLOUD_RUN_URL:-}"
if [ -n "$SERVICE_URL" ]; then
  SERVICE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$SERVICE_URL/health" 2>/dev/null || echo "000")
  [ "$SERVICE_STATUS" = "200" ] && pass "Cloud Run service — /health" || fail "Cloud Run /health — HTTP $SERVICE_STATUS"
else
  warn "CLOUD_RUN_URL not set — skipping Cloud Run check"
fi

# =============================================
# 5. GITHUB REPO SYNC CHECK
# =============================================
echo ""
echo "--- 5. GitHub Repo Sync ---"

if git rev-parse --git-dir > /dev/null 2>&1; then
  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse origin/main 2>/dev/null || echo "unknown")
  [ "$LOCAL" = "$REMOTE" ] && pass "Local HEAD matches origin/main" || warn "Local HEAD diverges from origin/main"
  DIRTY=$(git status --porcelain)
  [ -z "$DIRTY" ] && pass "Working tree clean" || warn "Uncommitted changes present"
else
  warn "Not a git repository — skipping repo sync check"
fi

# =============================================
# 6. CHANGELOG + VERSION CHECK
# =============================================
echo ""
echo "--- 6. Version & Changelog ---"

if [ -f "manifest.json" ]; then
  VERSION=$(node -e "console.log(require('./manifest.json').version)" 2>/dev/null || echo "")
  [ -n "$VERSION" ] && pass "manifest.json version: $VERSION" || fail "manifest.json version field missing"
fi

if [ -f "CHANGELOG.md" ]; then
  LINES=$(wc -l < CHANGELOG.md)
  [ "$LINES" -gt 0 ] && pass "CHANGELOG.md has content ($LINES lines)" || warn "CHANGELOG.md is empty"
fi

# =============================================
# SUMMARY
# =============================================
echo ""
echo "========================================"
echo "VERIFICATION SUMMARY"
echo "========================================"
echo "Timestamp : $TIMESTAMP"
echo "PASS      : $PASS"
echo "WARN      : $WARN"
echo "FAIL      : $FAIL"
TOTAL=$((PASS+WARN+FAIL))
PASS_RATE=$(echo "scale=1; $PASS * 100 / $TOTAL" | bc 2>/dev/null || echo "N/A")
echo "Pass Rate : $PASS_RATE%"
echo ""

# Write machine-readable JSON report
cat > "$REPORT_JSON" << EOF
{
  "timestamp": "$TIMESTAMP",
  "pass": $PASS,
  "warn": $WARN,
  "fail": $FAIL,
  "total": $TOTAL,
  "pass_rate": "$PASS_RATE%",
  "ci_mode": $CI_MODE
}
EOF
echo "Report written to $REPORT_JSON"

# Exit code
if [ "$FAIL" -gt 0 ]; then
  echo "Build verification FAILED ($FAIL failures)"
  [ "$CI_MODE" = "true" ] && exit 1 || exit 0
else
  echo "Build verification PASSED"
  exit 0
fi
