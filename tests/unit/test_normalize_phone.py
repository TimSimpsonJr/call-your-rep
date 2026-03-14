"""Tests for normalize_phone() from scrapers.adapters.base."""

import pytest
from scrapers.adapters.base import normalize_phone


@pytest.mark.parametrize("input_phone,expected", [
    # Standard formats → normalized
    ("803-212-6016", "(803) 212-6016"),
    ("803.212.6016", "(803) 212-6016"),
    ("(803) 212-6016", "(803) 212-6016"),
    ("8032126016", "(803) 212-6016"),
    ("803 212 6016", "(803) 212-6016"),
    # With area code parens but no space
    ("(803)212-6016", "(803) 212-6016"),
    # Leading/trailing whitespace
    ("  803-212-6016  ", "(803) 212-6016"),
    # Already normalized → unchanged
    ("(803) 212-6016", "(803) 212-6016"),
    # Empty/blank → empty string
    ("", ""),
    ("   ", ""),
    # Partial number (7 digits) → passthrough
    ("378-0488", "378-0488"),
    # Number with extension text → extracts 10-digit portion
    ("803-212-6016 ext 123", "(803) 212-6016"),
    # Random non-phone text → passthrough
    ("Call the office", "Call the office"),
])
def test_normalize_phone(input_phone, expected):
    assert normalize_phone(input_phone) == expected
