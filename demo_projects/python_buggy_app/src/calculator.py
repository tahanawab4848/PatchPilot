"""
Simple calculator library.

Known defect (for PatchPilot demo):
    The `divide` function does not raise ZeroDivisionError when dividing by zero.
    Instead it silently returns 0, which corrupts downstream calculations.

Expected correct behaviour:
    divide(10, 0) should raise ZeroDivisionError.
    divide(10, 2) should return 5.0.
"""


def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    """
    Divide a by b.

    BUG: Returns 0.0 instead of raising ZeroDivisionError when b == 0.
    This was introduced in commit abc1234 when the guard was accidentally removed.
    """
    if b == 0:
        return 0.0   # <-- BUG: should raise ZeroDivisionError("division by zero")
    return a / b


def average(values: list) -> float:
    """Return the arithmetic mean of a list of numbers."""
    if not values:
        raise ValueError("Cannot compute average of an empty list.")
    total = sum(values)
    count = len(values)
    return divide(total, count)
