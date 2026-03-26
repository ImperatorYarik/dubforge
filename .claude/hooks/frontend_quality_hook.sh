#!/bin/bash
# PostToolUse hook — quality checks for frontend files.
# Runs: ESLint (lint), Vitest (unit tests).
# Triggers only when a .vue or .js file inside frontend/src/ is written or edited.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only trigger for .vue/.js files under frontend/src/
echo "$FILE_PATH" | grep -qE '.*/frontend/src/.*\.(vue|js)$' || exit 0

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FRONTEND="$PROJECT_ROOT/frontend"

# Skip silently if dependencies aren't installed yet
if [ ! -d "$FRONTEND/node_modules" ]; then
    echo "⚠  frontend/node_modules not found — run 'npm install' in frontend/ to enable quality checks"
    exit 0
fi

cd "$FRONTEND"
FAIL=0

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  Frontend Quality Checks             ║"
echo "╚══════════════════════════════════════╝"

# ── 1. ESLint ────────────────────────────────────────────────────────────────
echo ""
echo "── ESLint (lint) ──────────────────────"
ESLINT_OUT=$(npm run lint 2>&1)
ESLINT_EXIT=$?

if [ "$ESLINT_EXIT" -ne 0 ]; then
    echo "$ESLINT_OUT"
    echo "✗ lint errors found — must fix before merging"
    FAIL=1
else
    WARN_COUNT=$(echo "$ESLINT_OUT" | grep -c 'warning' || true)
    if [ "$WARN_COUNT" -gt 0 ]; then
        echo "$ESLINT_OUT"
        echo "⚠  $WARN_COUNT warning(s)"
    else
        echo "✓ clean"
    fi
fi

# ── 2. Vitest ────────────────────────────────────────────────────────────────
echo ""
echo "── Vitest (unit tests) ────────────────"
VITEST_OUT=$(npm run test 2>&1)
VITEST_EXIT=$?

if [ "$VITEST_EXIT" -ne 0 ]; then
    echo "$VITEST_OUT"
    echo "✗ test(s) failed"
    FAIL=1
else
    SUMMARY=$(echo "$VITEST_OUT" | grep -E 'Tests |Test Files' | tail -2)
    echo "✓ ${SUMMARY:-all tests passed}"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
if [ "$FAIL" -ne 0 ]; then
    echo "╔══════════════════════════════════════╗"
    echo "║  ✗ Quality checks FAILED             ║"
    echo "╚══════════════════════════════════════╝"
    exit 1
else
    echo "╔══════════════════════════════════════╗"
    echo "║  ✓ All quality checks passed         ║"
    echo "╚══════════════════════════════════════╝"
    exit 0
fi
