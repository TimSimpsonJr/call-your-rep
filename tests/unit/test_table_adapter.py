"""Tests for the TableAdapter shared adapter."""

import pytest

from scrapers.adapters.table_adapter import TableAdapter, HEADER_PATTERNS
from tests.conftest import load_fixture, make_adapter


@pytest.fixture
def adapter():
    return make_adapter(TableAdapter)


@pytest.fixture
def basic_html():
    return load_fixture("table_basic.html")


class TestTableAdapterParse:
    """Tests for TableAdapter.parse() with a standard HTML table."""

    def test_extracts_three_members(self, adapter, basic_html):
        members = adapter.parse(basic_html)
        assert len(members) == 3

    def test_reverses_comma_name(self, adapter, basic_html):
        """'Smith, John' should become 'John Smith'."""
        members = adapter.parse(basic_html)
        assert members[0]["name"] == "John Smith"

    def test_no_comma_name_unchanged(self, adapter, basic_html):
        """'Jane Williams' has no comma, stays as-is."""
        members = adapter.parse(basic_html)
        assert members[1]["name"] == "Jane Williams"

    def test_strips_honorific(self, adapter, basic_html):
        """'Mr. Bob Brown' should become 'Bob Brown'."""
        members = adapter.parse(basic_html)
        assert members[2]["name"] == "Bob Brown"

    def test_district_column_applied_to_title(self, adapter, basic_html):
        """District column values should appear in titles."""
        members = adapter.parse(basic_html)
        # Row 1: title is "Chairman", district is "1" -> "Chairman, District 1"
        assert members[0]["title"] == "Chairman, District 1"
        # Row 2: title is empty, district is "2" -> "Council Member, District 2"
        assert members[1]["title"] == "Council Member, District 2"
        # Row 3: title is empty, district is "3" -> "Council Member, District 3"
        assert members[2]["title"] == "Council Member, District 3"

    def test_email_from_mailto_link(self, adapter, basic_html):
        """Email extracted from mailto: href."""
        members = adapter.parse(basic_html)
        assert members[0]["email"] == "jsmith@example.gov"

    def test_email_from_plain_text(self, adapter, basic_html):
        """Email extracted from plain text with @ sign."""
        members = adapter.parse(basic_html)
        assert members[1]["email"] == "jwilliams@example.gov"

    def test_phone_extracted(self, adapter, basic_html):
        """Phone numbers extracted from text and tel links."""
        members = adapter.parse(basic_html)
        assert members[0]["phone"] == "(555) 111-1111"
        assert members[2]["phone"] == "(555) 333-3333"


class TestTableAdapterColumnDetection:
    """Tests for _detect_columns header pattern matching."""

    def test_name_column_detected(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<th>Council Member Name</th>", "html.parser")
        adapter = make_adapter(TableAdapter)
        col_map = adapter._detect_columns(soup.find_all("th"))
        assert "name" in col_map

    def test_email_column_detected(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<th>E-Mail</th>", "html.parser")
        adapter = make_adapter(TableAdapter)
        col_map = adapter._detect_columns(soup.find_all("th"))
        assert "email" in col_map

    def test_phone_column_detected(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<th>Telephone</th>", "html.parser")
        adapter = make_adapter(TableAdapter)
        col_map = adapter._detect_columns(soup.find_all("th"))
        assert "phone" in col_map

    def test_district_column_detected(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<th>Ward</th>", "html.parser")
        adapter = make_adapter(TableAdapter)
        col_map = adapter._detect_columns(soup.find_all("th"))
        assert "district" in col_map

    def test_unknown_header_ignored(self):
        from bs4 import BeautifulSoup
        soup = BeautifulSoup("<th>Notes</th>", "html.parser")
        adapter = make_adapter(TableAdapter)
        col_map = adapter._detect_columns(soup.find_all("th"))
        assert len(col_map) == 0


class TestTableAdapterExcludeFilter:
    """Tests for _should_exclude filtering."""

    def test_excludes_clerk(self):
        record = {"name": "Jane Doe", "title": "County Clerk"}
        assert TableAdapter._should_exclude(record, ["clerk"]) is True

    def test_does_not_exclude_council_member(self):
        record = {"name": "Jane Doe", "title": "Council Member"}
        assert TableAdapter._should_exclude(record, ["clerk", "administrator"]) is False

    def test_excludes_by_name(self):
        record = {"name": "City Administrator", "title": ""}
        assert TableAdapter._should_exclude(record, ["administrator"]) is True
