#!/bin/bash
# PostToolUse hook — quality checks for worker/ Python files.
# Runs: Pylint (lint), Bandit (security), Radon (complexity), Pytest (unit tests).
# Triggers only when a .py file inside worker/ is written or edited.

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only trigger for Python files under worker/
case "$FILE_PATH" in
    */worker/*.py) ;;
    *) exit 0 ;;
esac

PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_ROOT/worker"

PYTHON="$PROJECT_ROOT/.venv/bin/python"
BIN="$PROJECT_ROOT/.venv/bin"
FAIL=0

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  worker Quality Checks                  ║"
echo "╚══════════════════════════════════════╝"

# ── 1. Pylint ────────────────────────────────────────────────────────────────
echo ""
echo "── Pylint (lint) ──────────────────────"
PYLINT_OUT=$(PYTHONPATH=. "$PYTHON" -m pylint app/ --score=no 2>&1)
PYLINT_ERRORS=$(echo "$PYLINT_OUT" | grep -cE ': E[0-9]' || true)
PYLINT_WARNS=$(echo "$PYLINT_OUT" | grep -cE ': W[0-9]' || true)

if [ "$PYLINT_ERRORS" -gt 0 ]; then
    echo "$PYLINT_OUT"
    echo "✗ $PYLINT_ERRORS error(s) — must fix before merging"
    FAIL=1
elif [ "$PYLINT_WARNS" -gt 0 ]; then
    echo "$PYLINT_OUT"
    echo "⚠  $PYLINT_WARNS warning(s)"
else
    echo "✓ clean"
fi

# ── 2. Bandit ────────────────────────────────────────────────────────────────
echo ""
echo "── Bandit (security) ──────────────────"
# -ll = medium+ severity; --skip B108 = allow intentional /tmp/ usage
BANDIT_OUT=$("$BIN/bandit" -r app/ -ll -q --skip B108 2>&1)
BANDIT_EXIT=$?
BANDIT_ISSUES=$(echo "$BANDIT_OUT" | grep -cE '>> Issue:' || true)

if [ "$BANDIT_EXIT" -ne 0 ] && [ "$BANDIT_ISSUES" -gt 0 ]; then
    echo "$BANDIT_OUT"
    echo "✗ $BANDIT_ISSUES security issue(s) (medium+ severity) — must fix"
    FAIL=1
else
    echo "✓ no medium/high security issues"
fi

# ── 3. Radon ─────────────────────────────────────────────────────────────────
echo ""
echo "── Radon (cyclomatic complexity) ──────"
# -n C = report only grade C (CC 11-15) and above; -s = show complexity score
RADON_HIGH=$("$BIN/radon" cc app/ -n C -s 2>&1)
# -n B = report grade B (CC 6-10) and above for informational display
RADON_B=$("$BIN/radon" cc app/ -n B -s 2>&1)

if [ -n "$RADON_HIGH" ]; then
    echo "$RADON_HIGH"
    echo "⚠  grade C+ complexity detected — consider refactoring"
elif [ -n "$RADON_B" ]; then
    echo "$RADON_B"
    echo "  (grade B — acceptable, informational only)"
else
    echo "✓ all functions grade A"
fi

# ── 4. Pytest ────────────────────────────────────────────────────────────────
echo ""
echo "── Pytest (unit tests) ────────────────"
PYTEST_OUT=$(PYTHONPATH=. "$PYTHON" -m pytest tests/ -q --tb=short 2>&1)
PYTEST_EXIT=$?

if [ "$PYTEST_EXIT" -ne 0 ]; then
    echo "$PYTEST_OUT"
    echo "✗ test(s) failed"
    FAIL=1
else
    SUMMARY=$(echo "$PYTEST_OUT" | tail -1)
    echo "✓ $SUMMARY"
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
