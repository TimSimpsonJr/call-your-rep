"""Tests for GenericMailto adapter parsing logic."""

import pytest
from scrapers.adapters.generic_mailto import GenericMailtoAdapter
from tests.conftest import load_fixture, make_adapter


@pytest.fixture
def adapter():
    return make_adapter(GenericMailtoAdapter)


@pytest.fixture
def basic_html():
    return load_fixture("generic_mailto.html")


# ---------------------------------------------------------------------------
# TestGenericMailtoParse
# ---------------------------------------------------------------------------

class TestGenericMailtoParse:
    """Parse generic_mailto.html: entry-content container with mailto links."""

    def test_finds_entry_content_container(self, adapter, basic_html):
        """The adapter should locate the entry-content div and parse it."""
        members = adapter.parse(basic_html)
        assert len(members) >= 1

    def test_extracts_three_members(self, adapter, basic_html):
        members = adapter.parse(basic_html)
        assert len(members) == 3

    def test_mayor_title_extracted(self, adapter, basic_html):
        members = adapter.parse(basic_html)
        by_name = {m["name"]: m for m in members}
        assert "Alice Johnson" in by_name
        assert by_name["Alice Johnson"]["title"] == "Mayor"

    def test_mayor_name_stripped_of_prefix(self, adapter, basic_html):
        members = adapter.parse(basic_html)
        names = [m["name"] for m in members]
        assert "Mayor Alice Johnson" not in names
        assert "Alice Johnson" in names

    def test_mayor_email(self, adapter, basic_html):
        members = adapter.parse(basic_html)
        by_name = {m["name"]: m for m in members}
        assert by_name["Alice Johnson"]["email"] == "ajohnson@city.gov"

    def test_mayor_phone_from_tel_link(self, adapter, basic_html):
        members = adapter.parse(basic_html)
        by_name = {m["name"]: m for m in members}
        assert by_name["Alice Johnson"]["phone"] == "(803) 555-0001"

    def test_second_member_no_phone(self, adapter, basic_html):
        members = adapter.parse(basic_html)
        by_name = {m["name"]: m for m in members}
        assert by_name["Bob Williams"]["phone"] == ""

    def test_second_member_email(self, adapter, basic_html):
        members = adapter.parse(basic_html)
        by_name = {m["name"]: m for m in members}
        assert by_name["Bob Williams"]["email"] == "bwilliams@city.gov"

    def test_third_member_default_title(self, adapter, basic_html):
        members = adapter.parse(basic_html)
        by_name = {m["name"]: m for m in members}
        assert by_name["Carol Davis"]["title"] == "Council Member"

    def test_mayor_sorted_first(self, adapter, basic_html):
        members = adapter.parse(basic_html)
        assert members[0]["title"] == "Mayor"


# ---------------------------------------------------------------------------
# TestGenericMailtoContentDetection
# ---------------------------------------------------------------------------

class TestGenericMailtoContentDetection:
    """Content area detection across different CSS selectors."""

    MEMBER_HTML = """
        <strong>Test Person</strong>
        <a href="mailto:test@city.gov">test@city.gov</a>
    """

    def test_et_pb_section_detected(self, adapter):
        """Divi WordPress theme container is recognized."""
        html = f"""<html><body>
        <div class="et_pb_section">{self.MEMBER_HTML}</div>
        </body></html>"""
        members = adapter.parse(html)
        assert len(members) == 1
        assert members[0]["name"] == "Test Person"

    def test_node_content_detected(self, adapter):
        """Drupal node__content container is recognized."""
        html = f"""<html><body>
        <div class="node__content">{self.MEMBER_HTML}</div>
        </body></html>"""
        members = adapter.parse(html)
        assert len(members) == 1
        assert members[0]["name"] == "Test Person"

    def test_custom_content_selector(self):
        """adapterConfig.contentSelector overrides default selectors."""
        adapter = make_adapter(GenericMailtoAdapter, {
            "adapterConfig": {"contentSelector": "#my-custom-area"},
        })
        html = f"""<html><body>
        <div id="other">{self.MEMBER_HTML}</div>
        <div id="my-custom-area">
            <strong>Custom Person</strong>
            <a href="mailto:custom@city.gov">custom@city.gov</a>
        </div>
        </body></html>"""
        members = adapter.parse(html)
        assert len(members) == 1
        assert members[0]["name"] == "Custom Person"

    def test_falls_through_to_body(self, adapter):
        """When no known container matches, falls through to body."""
        html = f"""<html><body>
        {self.MEMBER_HTML}
        </body></html>"""
        members = adapter.parse(html)
        assert len(members) == 1
        assert members[0]["name"] == "Test Person"

    def test_field_name_body_detected(self, adapter):
        """Drupal field--name-body container is recognized."""
        html = f"""<html><body>
        <div class="field--name-body">{self.MEMBER_HTML}</div>
        </body></html>"""
        members = adapter.parse(html)
        assert len(members) == 1
        assert members[0]["name"] == "Test Person"

    def test_elementor_detected(self, adapter):
        """Elementor WordPress container is recognized."""
        html = f"""<html><body>
        <div class="elementor-widget-wrap">{self.MEMBER_HTML}</div>
        </body></html>"""
        members = adapter.parse(html)
        assert len(members) == 1
        assert members[0]["name"] == "Test Person"

    def test_content_area_class_detected(self, adapter):
        """Granicus / generic content_area class is recognized."""
        html = f"""<html><body>
        <div class="content_area">{self.MEMBER_HTML}</div>
        </body></html>"""
        members = adapter.parse(html)
        assert len(members) == 1
        assert members[0]["name"] == "Test Person"

    def test_article_tag_detected(self, adapter):
        """Falls through to <article> tag when no class-based container matches."""
        html = f"""<html><body>
        <article>{self.MEMBER_HTML}</article>
        </body></html>"""
        members = adapter.parse(html)
        assert len(members) == 1
        assert members[0]["name"] == "Test Person"

    def test_main_tag_detected(self, adapter):
        """Falls through to <main> tag."""
        html = f"""<html><body>
        <main>{self.MEMBER_HTML}</main>
        </body></html>"""
        members = adapter.parse(html)
        assert len(members) == 1
        assert members[0]["name"] == "Test Person"
