#!/bin/bash
# =============================================================================
# iFinsure Deploy Script Verification Tests
# =============================================================================
# Lightweight tests for deploy.sh without external dependencies.
# Run: ./provisioning/test-deploy.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_SCRIPT="${SCRIPT_DIR}/deploy.sh"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

run_test() {
    local name="$1"
    local cmd="$2"
    ((TESTS_RUN++))
    log_test "$name"
    if eval "$cmd" >/dev/null 2>&1; then
        log_pass "$name"
        return 0
    else
        log_fail "$name"
        return 1
    fi
}

# =============================================================================
# SYNTAX TESTS
# =============================================================================

echo ""
echo "=========================================="
echo "  Deploy Script Verification Tests"
echo "=========================================="
echo ""

# Test 1: Script exists
run_test "deploy.sh exists" "[[ -f '$DEPLOY_SCRIPT' ]]"

# Test 2: Bash syntax check
run_test "Bash syntax valid" "bash -n '$DEPLOY_SCRIPT'"

# Test 3: Script is executable (or can be made so)
run_test "Script has shebang" "head -1 '$DEPLOY_SCRIPT' | grep -q '^#!/bin/bash'"

# Test 4: Strict mode enabled
run_test "Strict mode (set -euo pipefail)" "grep -q 'set -euo pipefail' '$DEPLOY_SCRIPT'"

# =============================================================================
# SECURITY TESTS
# =============================================================================

echo ""
echo "--- Security Checks ---"

# Test 5: No hardcoded passwords
run_test "No hardcoded passwords" "! grep -iE '(password|secret|key)\s*=\s*[\"'\''][^$\"'\'']+[\"'\'']' '$DEPLOY_SCRIPT' | grep -vE '(DB_PASSWORD=|SECRET_KEY=|PASSKEY=)'"

# Test 6: Environment file permissions set
run_test "Env file chmod 600" "grep -q 'chmod 600.*env_file' '$DEPLOY_SCRIPT'"

# Test 7: No eval with user input
run_test "No unsafe eval" "! grep -E 'eval\s+\"\\\$' '$DEPLOY_SCRIPT'"

# Test 8: ALLOW_INSTALL flag exists
run_test "ALLOW_INSTALL safety flag" "grep -q 'ALLOW_INSTALL' '$DEPLOY_SCRIPT'"

# =============================================================================
# ROBUSTNESS TESTS
# =============================================================================

echo ""
echo "--- Robustness Checks ---"

# Test 9: Error trap exists
run_test "Error trap configured" "grep -q 'trap.*cleanup_on_error.*ERR' '$DEPLOY_SCRIPT'"

# Test 10: Exit trap exists
run_test "Exit trap configured" "grep -q 'trap.*cleanup_on_exit.*EXIT' '$DEPLOY_SCRIPT'"

# Test 11: Input validation functions exist
run_test "Domain validation function" "grep -q 'validate_domain()' '$DEPLOY_SCRIPT'"
run_test "Email validation function" "grep -q 'validate_email()' '$DEPLOY_SCRIPT'"
run_test "Port validation function" "grep -q 'validate_port()' '$DEPLOY_SCRIPT'"

# Test 12: DRY_RUN mode exists
run_test "DRY_RUN mode supported" "grep -q 'DRY_RUN' '$DEPLOY_SCRIPT'"

# Test 13: Logging functions exist
run_test "Logging functions present" "grep -q 'log_error()' '$DEPLOY_SCRIPT'"

# =============================================================================
# IDEMPOTENCY TESTS
# =============================================================================

echo ""
echo "--- Idempotency Checks ---"

# Test 14: Docker network check before create
run_test "Docker network idempotent" "grep -q 'docker network ls.*ifinsure_network' '$DEPLOY_SCRIPT'"

# Test 15: Cron job idempotent marker
run_test "Cron job uses marker" "grep -q 'ifinsure-ssl-renewal' '$DEPLOY_SCRIPT'"

# Test 16: SSL config backup before overwrite
run_test "SSL config backup" "grep -q 'ssl_conf_backup' '$DEPLOY_SCRIPT'"

# =============================================================================
# ARGUMENT PARSING TESTS
# =============================================================================

echo ""
echo "--- Argument Parsing (Dry Run) ---"

# Test 17: Help flag works
run_test "--help exits 0" "bash '$DEPLOY_SCRIPT' --help"

# Test 18: Invalid domain rejected
((TESTS_RUN++))
log_test "Invalid domain rejected"
if bash "$DEPLOY_SCRIPT" --domain "invalid..domain" --dry-run 2>&1 | grep -q "Invalid domain"; then
    log_pass "Invalid domain rejected"
else
    log_fail "Invalid domain rejected"
fi

# Test 19: Invalid email rejected  
((TESTS_RUN++))
log_test "Invalid email rejected"
if bash "$DEPLOY_SCRIPT" --domain "test.com" --email "notanemail" --dry-run 2>&1 | grep -q "Invalid email"; then
    log_pass "Invalid email rejected"
else
    log_fail "Invalid email rejected"
fi

# Test 20: Invalid port rejected
((TESTS_RUN++))
log_test "Invalid port rejected"
if bash "$DEPLOY_SCRIPT" --port "99999" --dry-run 2>&1 | grep -q "Invalid port"; then
    log_pass "Invalid port rejected"
else
    log_fail "Invalid port rejected"
fi

# =============================================================================
# OPTIONAL: SHELLCHECK (if available)
# =============================================================================

echo ""
echo "--- Optional: ShellCheck ---"

if command -v shellcheck &>/dev/null; then
    ((TESTS_RUN++))
    log_test "ShellCheck analysis"
    # Run shellcheck with common exclusions for acceptable patterns
    if shellcheck -e SC1091,SC2034,SC2155 "$DEPLOY_SCRIPT" 2>&1; then
        log_pass "ShellCheck analysis"
    else
        log_fail "ShellCheck analysis (warnings found)"
    fi
else
    echo -e "${YELLOW}[SKIP]${NC} ShellCheck not installed (optional)"
fi

# =============================================================================
# SUMMARY
# =============================================================================

echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="
echo ""
echo -e "  Tests Run:    ${TESTS_RUN}"
echo -e "  ${GREEN}Passed:       ${TESTS_PASSED}${NC}"
echo -e "  ${RED}Failed:       ${TESTS_FAILED}${NC}"
echo ""

if [[ $TESTS_FAILED -eq 0 ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Review output above.${NC}"
    exit 1
fi
