"""Tests for helper functions in scrapers.state."""

import pytest
from scrapers.state import _abbreviate_party, _first_link


class TestAbbreviateParty:
    @pytest.mark.parametrize("party,expected", [
        ("Democratic", "D"),
        ("democratic", "D"),
        ("Democrat", "D"),
        ("Republican", "R"),
        ("republican", "R"),
        ("Independent", "I"),
        ("", ""),
        # These hit the fallback: first char uppercased
        ("Libertarian", "L"),
        ("Green", "G"),
        ("  Republican  ", "R"),
    ])
    def test_abbreviate_party(self, party, expected):
        assert _abbreviate_party(party) == expected


class TestFirstLink:
    @pytest.mark.parametrize("links_str,expected", [
        # Semicolon-separated -> first URL
        ("https://a.com; https://b.com", "https://a.com"),
        # Single URL
        ("https://example.com", "https://example.com"),
        # Empty/blank
        ("", ""),
        ("   ", ""),
        # Whitespace around URL
        ("  https://example.com  ", "https://example.com"),
        # Multiple semicolons
        ("https://a.com;https://b.com;https://c.com", "https://a.com"),
    ])
    def test_first_link(self, links_str, expected):
        assert _first_link(links_str) == expected
