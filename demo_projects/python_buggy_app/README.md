# python_buggy_app — PatchPilot Demo Project

## Purpose

This project is the canonical demonstration for PatchPilot. It contains a
**deliberate, reproducible bug** that PatchPilot must diagnose, patch, and verify.

## The Bug

**File:** `src/calculator.py`  
**Function:** `divide(a, b)`  
**Description:** When the divisor `b` is zero, the function silently returns `0.0`
instead of raising `ZeroDivisionError`. This hides division-by-zero errors from
callers and corrupts downstream calculations such as `average()`.

## Reproducing the Failure

```bash
cd demo_projects/python_buggy_app
pip install -r requirements.txt
pytest
```

Expected output (with the bug present):

```
FAILED tests/test_calculator.py::test_divide_by_zero - Failed: DID NOT RAISE
FAILED tests/test_calculator.py::test_divide_by_zero_message - Failed: DID NOT RAISE
```

All other tests pass (regression baseline).

## The Correct Fix

Change the guard in `divide()` from:

```python
if b == 0:
    return 0.0
```

to:

```python
if b == 0:
    raise ZeroDivisionError("division by zero")
```

After the fix, all 11 tests should pass.

## Why Two Failing Tests?

`test_divide_by_zero_message` verifies that the error message matches
`"division by zero"`. This ensures the agent cannot satisfy the test suite
by raising a blank `ZeroDivisionError()` or by deleting the test.

## Bug Description (for PatchPilot input)

> The `divide` function in `src/calculator.py` returns `0.0` instead of raising
> `ZeroDivisionError` when the divisor is zero. Tests `test_divide_by_zero` and
> `test_divide_by_zero_message` both fail. The fix should raise
> `ZeroDivisionError("division by zero")` inside the zero-guard.
