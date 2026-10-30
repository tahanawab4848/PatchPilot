"""
Tests for the calculator library.

test_divide_by_zero FAILS against the buggy implementation.
All other tests pass, establishing a regression baseline.
"""

import pytest
from src.calculator import add, average, divide, multiply, subtract


# ── Passing tests (regression baseline) ────────────────────────────────────────

def test_add_positive():
    assert add(2, 3) == 5


def test_add_negative():
    assert add(-1, -1) == -2


def test_subtract():
    assert subtract(10, 4) == 6


def test_multiply():
    assert multiply(3, 4) == 12


def test_divide_normal():
    assert divide(10, 2) == 5.0


def test_divide_float_result():
    assert divide(1, 3) == pytest.approx(0.3333, rel=1e-3)


def test_average_basic():
    assert average([1, 2, 3, 4, 5]) == 3.0


def test_average_single():
    assert average([42]) == 42.0


def test_average_empty_raises():
    with pytest.raises(ValueError, match="empty"):
        average([])


# ── Failing test — demonstrates the bug ────────────────────────────────────────

def test_divide_by_zero():
    """
    EXPECTED: divide(10, 0) raises ZeroDivisionError.
    ACTUAL (buggy): divide(10, 0) returns 0.0 — this test FAILS.
    """
    with pytest.raises(ZeroDivisionError):
        divide(10, 0)


# ── Negative case: fix must not simply remove the test ─────────────────────────

def test_divide_by_zero_message():
    """
    Verifies that the ZeroDivisionError carries a meaningful message.
    Ensures a trivial 'raise ZeroDivisionError()' is not sufficient.
    """
    with pytest.raises(ZeroDivisionError, match="division by zero"):
        divide(5, 0)
