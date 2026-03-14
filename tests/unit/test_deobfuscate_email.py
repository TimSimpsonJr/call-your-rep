"""Tests for deobfuscate_cf_email() from scrapers.adapters.base."""

import pytest
from scrapers.adapters.base import deobfuscate_cf_email


def _encode_cf_email(email: str, key: int = 0x5A) -> str:
    """Encode an email using Cloudflare's XOR scheme for test fixtures."""
    result = format(key, "02x")
    for ch in email:
        result += format(ord(ch) ^ key, "02x")
    return result


class TestDeobfuscateCfEmail:
    def test_basic_decode(self):
        encoded = _encode_cf_email("john@city.gov")
        assert deobfuscate_cf_email(encoded) == "john@city.gov"

    def test_different_key(self):
        encoded = _encode_cf_email("mayor@town.sc.us", key=0x2F)
        assert deobfuscate_cf_email(encoded) == "mayor@town.sc.us"

    def test_special_characters(self):
        encoded = _encode_cf_email("jane.doe+council@city.gov")
        assert deobfuscate_cf_email(encoded) == "jane.doe+council@city.gov"

    def test_empty_string(self):
        assert deobfuscate_cf_email("") == ""

    def test_invalid_hex(self):
        assert deobfuscate_cf_email("ZZZZ") == ""

    def test_single_byte_key_only(self):
        # Just the key byte, no encoded chars → empty email
        assert deobfuscate_cf_email("5a") == ""
