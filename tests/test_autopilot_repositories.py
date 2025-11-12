"""
Unit tests for Autopilot repository helpers.
"""

from app.domain.usinage.fastems1.autopilot.repositories import _coerce_int


def test_coerce_int_limits_large_values():
    max_int = 2_147_483_647
    expected = 8420339008 % max_int or max_int
    assert _coerce_int(8420339008, None) == expected


def test_coerce_int_fallback_to_hash_when_no_digits():
    value = _coerce_int(None, "WORK-ORDER")
    assert 0 < value <= 2_147_483_647
