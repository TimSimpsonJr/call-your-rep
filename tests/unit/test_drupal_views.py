"""Tests for the DrupalViewsAdapter shared adapter."""

import pytest

from scrapers.adapters.drupal_views import DrupalViewsAdapter
from tests.conftest import load_fixture, make_adapter


@pytest.fixture
def adapter():
    return make_adapter(DrupalViewsAdapter)


class TestDrupalViewsRowPattern:
    """Tests for views-row pattern parsing."""

    @pytest.fixture
    def members(self, adapter):
        html = load_fixture("drupal_views_row.html")
        return adapter.parse(html)

    def test_extracts_two_members(self, members):
        assert len(members) == 2

    def test_name_from_link(self, members):
        """First member name comes from an <a> tag."""
        names = [m["name"] for m in members]
        assert "Alice Johnson" in names

    def test_name_from_plain_text(self, members):
        """Second member name is plain text, no link."""
        names = [m["name"] for m in members]
        assert "Carlos Rivera" in names

    def test_chairman_title_with_district(self, members):
        """Chairman + district 1 -> 'Chairman, District 1'."""
        alice = next(m for m in members if m["name"] == "Alice Johnson")
        assert alice["title"] == "Chairman, District 1"

    def test_empty_job_title_with_district(self, members):
        """No job title + district 2 -> 'Council Member, District 2'."""
        carlos = next(m for m in members if m["name"] == "Carlos Rivera")
        assert carlos["title"] == "Council Member, District 2"

    def test_email_from_mailto(self, members):
        alice = next(m for m in members if m["name"] == "Alice Johnson")
        assert alice["email"] == "ajohnson@example.gov"

    def test_email_from_text(self, members):
        carlos = next(m for m in members if m["name"] == "Carlos Rivera")
        assert carlos["email"] == "crivera@example.gov"

    def test_phone_from_tel_link(self, members):
        alice = next(m for m in members if m["name"] == "Alice Johnson")
        assert alice["phone"] == "(555) 123-4567"

    def test_phone_from_text(self, members):
        carlos = next(m for m in members if m["name"] == "Carlos Rivera")
        assert carlos["phone"] == "(555) 765-4321"

    def test_sort_order(self, members):
        """Chairman should sort before regular council member."""
        assert members[0]["name"] == "Alice Johnson"
        assert members[1]["name"] == "Carlos Rivera"


class TestDrupalPersonItemPattern:
    """Tests for person-item article parsing."""

    @pytest.fixture
    def members(self, adapter):
        html = load_fixture("drupal_person_item.html")
        return adapter.parse(html)

    def test_extracts_two_members(self, members):
        assert len(members) == 2

    def test_mayor_title(self, members):
        diana = next(m for m in members if m["name"] == "Diana Ross")
        assert diana["title"] == "Mayor"

    def test_councilman_title_passthrough(self, members):
        """'Councilman' is not a recognized keyword, passed through as-is."""
        evan = next(m for m in members if m["name"] == "Evan Taylor")
        assert evan["title"] == "Councilman"

    def test_email_from_mailto(self, members):
        diana = next(m for m in members if m["name"] == "Diana Ross")
        assert diana["email"] == "dross@example.gov"

    def test_email_from_text(self, members):
        evan = next(m for m in members if m["name"] == "Evan Taylor")
        assert evan["email"] == "etaylor@example.gov"

    def test_phone_from_tel(self, members):
        diana = next(m for m in members if m["name"] == "Diana Ross")
        assert diana["phone"] == "(555) 999-8888"

    def test_phone_from_text(self, members):
        evan = next(m for m in members if m["name"] == "Evan Taylor")
        assert evan["phone"] == "(555) 777-6666"

    def test_sort_order(self, members):
        """Mayor should sort before regular council member."""
        assert members[0]["name"] == "Diana Ross"
        assert members[1]["name"] == "Evan Taylor"


class TestDrupalNormalizeTitle:
    """Parametrized tests for _normalize_title static method."""

    @pytest.mark.parametrize("raw,district,expected", [
        ("Mayor", "", "Mayor"),
        ("mayor", "", "Mayor"),
        ("Mayor Pro Tem", "", "Mayor Pro Tem"),
        ("mayor pro tem", "3", "Mayor Pro Tem, District 3"),
        ("Chairman", "", "Chairman"),
        ("chairman", "1", "Chairman, District 1"),
        ("Vice Chairman", "", "Vice Chairman"),
        ("Vice Chair", "2", "Vice Chairman, District 2"),
        ("Seat #4 Western", "", "Council Member, Seat 4"),
        ("District 5", "", "Council Member, District 5"),
        ("", "7", "Council Member, District 7"),
        ("", "", "Council Member"),
        ("Councilman", "", "Councilman"),
    ])
    def test_normalize_title(self, raw, district, expected):
        assert DrupalViewsAdapter._normalize_title(raw, district) == expected
