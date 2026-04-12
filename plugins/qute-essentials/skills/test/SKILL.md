---
name: test
description: Run the project's test suite and diagnose failures. Use when the user says "run tests", "check tests", "tests passing?", "why is X failing", or after a code change that might break tests. Detects the test framework (pytest, unittest, jest, cargo test, go test), runs it, parses failures, and explains what broke and why. If failures are found, proposes the smallest fix for each and offers to apply them.
argument-hint: "[path-or-filter]"
---

# /test

Run the test suite, interpret failures, and propose fixes.

## Step 1: Detect framework

Check in priority order:

```bash
# Python
[ -f pyproject.toml ] && grep -q pytest pyproject.toml && echo "pytest"
[ -f setup.cfg ] && grep -q pytest setup.cfg && echo "pytest"
[ -f pytest.ini ] && echo "pytest"
# JS/TS
[ -f package.json ] && grep -q '"test"' package.json && echo "npm test"
# Rust
[ -f Cargo.toml ] && echo "cargo test"
# Go
[ -f go.mod ] && echo "go test ./..."
```

Default to `pytest` if Python files exist and no other framework is detected.

## Step 2: Run tests

Run with the user's filter if `$ARGUMENTS` was provided (e.g. `/test test_pricing` passes `-k test_pricing` to pytest).

**pytest:**
```bash
python -m pytest $ARGUMENTS -x --tb=short -q 2>&1 | tail -60
```

**jest / npm test:**
```bash
npm test -- $ARGUMENTS 2>&1 | tail -60
```

**cargo test:**
```bash
cargo test $ARGUMENTS 2>&1 | tail -60
```

**go test:**
```bash
go test ./... $ARGUMENTS 2>&1 | tail -60
```

Use `-x` / fail-fast where supported so failures are not buried.

## Step 3: Interpret output

For each failing test, report:

```
FAIL  test_name
  File: path/to/test.py:42
  Expected: <value>
  Got:      <value>
  Likely cause: <1 sentence>
```

Group failures by root cause when multiple tests fail for the same reason (e.g. all failing because a function signature changed).

## Step 4: Propose fixes

For each failure (or failure group):
- State the fix in one sentence
- Show the minimal code change
- Ask once: "Apply this fix?" — do not apply without confirmation

If more than 3 distinct root causes exist, ask the user which to tackle first rather than dumping all proposals.

## Step 5: If all tests pass

Report:
```
All tests passing (N tests, 0 failures)
```

No further action needed.

## Notes

- Do not modify test files to make tests pass — fix the implementation.
- If tests were already failing before the current session's changes, note that they are pre-existing failures and do not attempt to fix them unless asked.
- For slow test suites, suggest `$ARGUMENTS` filters to scope the run.
