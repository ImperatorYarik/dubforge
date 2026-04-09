---
name: api-tdd-workflow
description: This skill should be used when writing any backend API code, following TDD for FastAPI endpoints, writing failing tests before production code, or running the pytest suite.
version: 1.0.0
---

# API TDD Workflow

## The TDD Cycle (MANDATORY — no exceptions)

1. **RED** — Write a failing test that describes the desired behaviour. Run it. Confirm it fails with a meaningful error (not a syntax error).
2. **GREEN** — Write the minimum production code to make the test pass. No extra logic — only what the test requires.
3. **REFACTOR** — Clean up, extract helpers, remove duplication. Keep all tests green throughout.
4. **Repeat** for each behaviour slice.

**For bug fixes:** Write a test that reproduces the bug first (it will fail). Then fix the bug. The test is the regression guard.

Never write production code without a failing test first. Never skip refactor.

## Running Tests

```bash
cd api
pip install -r requirements.txt
pytest                                    # all tests
pytest tests/test_routers_projects.py     # single file
pytest -k "test_name"                     # single test
pytest -x                                 # stop on first failure (use during RED phase)
pytest --tb=short                         # brief tracebacks
```

## Self-Verification Checklist

Before presenting any implementation, verify every item:

- [ ] Failing test written and confirmed failing **before** any production code
- [ ] All three TDD phases completed (RED → GREEN → REFACTOR)
- [ ] Happy path, side effects, and error paths tested
- [ ] Mocks patch at the router boundary
- [ ] Router delegates to service/repo — no logic leak
- [ ] Repository uses async Motor correctly
- [ ] Pydantic models type-annotated with v2 syntax
- [ ] Error handling follows layered convention
- [ ] No hardcoded values
- [ ] All tests pass with `pytest`
