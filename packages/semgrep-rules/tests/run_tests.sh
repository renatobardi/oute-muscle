#!/usr/bin/env bash
# Run all Semgrep rule tests and report results.
# Usage: ./tests/run_tests.sh [--verbose]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RULES_DIR="$(cd "$SCRIPT_DIR/../rules" && pwd)"

VERBOSE="${1:-}"
PASS=0
FAIL=0
ERRORS=()

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
RESET='\033[0m'

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Oute Muscle — Semgrep Rule Tests"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ! command -v semgrep &>/dev/null; then
  echo -e "${RED}ERROR: semgrep not found. Install with: pip install semgrep${RESET}"
  exit 1
fi

for category_dir in "$RULES_DIR"/*/; do
  category="$(basename "$category_dir")"

  for yaml_file in "$category_dir"*.yaml; do
    [ -f "$yaml_file" ] || continue
    rule_id="$(basename "$yaml_file" .yaml)"
    test_file="$category_dir${rule_id}.test.py"

    if [ ! -f "$test_file" ]; then
      echo -e "${YELLOW}SKIP${RESET}  $rule_id (no test file)"
      continue
    fi

    if [ -n "$VERBOSE" ]; then
      echo "Testing $rule_id ..."
      semgrep --test --test-ignore-todo "$yaml_file" 2>&1 || {
        FAIL=$((FAIL + 1))
        ERRORS+=("$rule_id")
        echo -e "${RED}FAIL${RESET}  $rule_id"
        continue
      }
    else
      output=$(semgrep --test --test-ignore-todo "$yaml_file" 2>&1) || {
        FAIL=$((FAIL + 1))
        ERRORS+=("$rule_id")
        echo -e "${RED}FAIL${RESET}  $rule_id"
        if [ -n "$VERBOSE" ]; then echo "$output"; fi
        continue
      }
    fi

    PASS=$((PASS + 1))
    echo -e "${GREEN}PASS${RESET}  $rule_id"
  done
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Results: ${PASS} passed, ${FAIL} failed"

if [ ${#ERRORS[@]} -gt 0 ]; then
  echo -e "${RED}  Failed rules:${RESET}"
  for err in "${ERRORS[@]}"; do
    echo "    - $err"
  done
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit 0
