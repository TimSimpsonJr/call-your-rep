# Test Suite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add unit and integration tests covering utility functions, shared adapter parsing, CI scripts, and data validation.

**Architecture:** Tests grouped by layer — `tests/unit/` for fast pure-function and minimal-HTML tests, `tests/integration/` for real-snapshot smoke tests, `tests/fixtures/` for HTML files. Each adapter's `parse()` is tested directly with hand-crafted HTML (no HTTP). Scripts tested with temp data dirs.

**Tech Stack:** pytest ≥8.0, existing Python 3.12+ and beautifulsoup4/requests from requirements.txt

**Design doc:** `docs/plans/2026-03-14-test-suite-design.md`

---

### Task 1: Scaffold test infrastructure

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/fixtures/html/.gitkeep`
- Create: `tests/fixtures/snapshots/.gitkeep`
- Create: `pytest.ini`

**Step 1: Create `requirements-dev.txt`**

```
# Dev/test dependencies — install with: pip install -r requirements-dev.txt
-r requirements.txt
pytest>=8.0,<9
```

**Step 2: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
markers =
    integration: marks tests that use real site HTML snapshots (deselect with '-m "not integration"')
```

**Step 3: Create `tests/conftest.py`**

```python
"""Shared test fixtures for open-civics tests."""

import os
import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
HTML_DIR = os.path.join(FIXTURES_DIR, "html")
SNAPSHOTS_DIR = os.path.join(FIXTURES_DIR, "snapshots")


def load_fixture(filename: str, subdir: str = "html") -> str:
    """Load an HTML fixture file by name."""
    base = HTML_DIR if subdir == "html" else SNAPSHOTS_DIR
    path = os.path.join(base, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def make_adapter(adapter_class, entry_overrides=None):
    """Create an adapter instance with a minimal entry dict.

    Usage:
        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
    """
    entry = {
        "id": "test-jurisdiction",
        "name": "Test Jurisdiction",
        "type": "place",
        "county": "Test",
        "url": "",
        "adapterConfig": {},
    }
    if entry_overrides:
        entry.update(entry_overrides)
    return adapter_class(entry)
```

**Step 4: Create empty `__init__.py` files and `.gitkeep` files**

Create empty files:
- `tests/__init__.py`
- `tests/unit/__init__.py`
- `tests/integration/__init__.py`
- `tests/fixtures/html/.gitkeep`
- `tests/fixtures/snapshots/.gitkeep`

**Step 5: Install dev deps and verify pytest runs**

Run: `pip install -r requirements-dev.txt && pytest --co -q`
Expected: "no tests ran" (collected 0 items)

**Step 6: Commit**

```bash
git add requirements-dev.txt pytest.ini tests/
git commit -m "test: scaffold test infrastructure with pytest"
```

---

### Task 2: Utility function tests — normalize_phone and deobfuscate_cf_email

**Files:**
- Create: `tests/unit/test_normalize_phone.py`
- Create: `tests/unit/test_deobfuscate_email.py`
- Reference: `scrapers/adapters/base.py:8-38` (source functions)

**Step 1: Write `tests/unit/test_normalize_phone.py`**

```python
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
```

**Step 2: Write `tests/unit/test_deobfuscate_email.py`**

```python
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
```

**Step 3: Run tests**

Run: `pytest tests/unit/test_normalize_phone.py tests/unit/test_deobfuscate_email.py -v`
Expected: All pass

**Step 4: Commit**

```bash
git add tests/unit/test_normalize_phone.py tests/unit/test_deobfuscate_email.py
git commit -m "test: add normalize_phone and deobfuscate_cf_email tests"
```

---

### Task 3: Utility function tests — state helpers and BaseAdapter

**Files:**
- Create: `tests/unit/test_state_helpers.py`
- Create: `tests/unit/test_base_adapter.py`
- Reference: `scrapers/state.py:66-81` (_abbreviate_party, _first_link)
- Reference: `scrapers/adapters/base.py:41-122` (BaseAdapter)

**Step 1: Write `tests/unit/test_state_helpers.py`**

```python
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
        ("Libertarian", "L"),
        ("Green", "G"),
        ("  Republican  ", "R"),
    ])
    def test_abbreviate_party(self, party, expected):
        assert _abbreviate_party(party) == expected


class TestFirstLink:
    @pytest.mark.parametrize("links_str,expected", [
        # Semicolon-separated → first URL
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
```

**Step 2: Write `tests/unit/test_base_adapter.py`**

```python
"""Tests for BaseAdapter contract from scrapers.adapters.base."""

import pytest
from scrapers.adapters.base import BaseAdapter


class StubAdapter(BaseAdapter):
    """Minimal concrete adapter for testing base class behavior."""

    def __init__(self, html="<html></html>", **kwargs):
        entry = {
            "id": "test-stub",
            "name": "Test Stub",
            "type": "place",
            "county": "Test",
            "url": "",
            "adapterConfig": {},
        }
        entry.update(kwargs)
        super().__init__(entry)
        self._test_html = html

    def fetch(self) -> str:
        return self._test_html

    def parse(self, html: str) -> list[dict]:
        return self._test_members


class TestValidate:
    def test_raises_on_empty_list(self):
        adapter = StubAdapter()
        with pytest.raises(ValueError, match="produced 0 records"):
            adapter.validate([])

    def test_warns_missing_name(self):
        adapter = StubAdapter()
        records = [{"title": "Council Member", "email": "a@b.com"}]
        result = adapter.validate(records)
        assert len(result) == 1
        assert any("no name" in w for w in adapter.warnings)

    def test_warns_missing_title(self):
        adapter = StubAdapter()
        records = [{"name": "John", "email": "a@b.com"}]
        adapter.validate(records)
        assert any("no title" in w for w in adapter.warnings)

    def test_warns_no_contact_info(self):
        adapter = StubAdapter()
        records = [{"name": "John", "title": "Mayor"}]
        adapter.validate(records)
        assert any("no email or phone" in w for w in adapter.warnings)

    def test_valid_record_no_warnings(self):
        adapter = StubAdapter()
        records = [{"name": "John", "title": "Mayor", "email": "j@city.gov"}]
        adapter.validate(records)
        assert adapter.warnings == []


class TestNormalize:
    def test_normalizes_phone(self):
        adapter = StubAdapter()
        records = [{"name": "John", "phone": "803-555-1234"}]
        result = adapter.normalize(records)
        assert result[0]["phone"] == "(803) 555-1234"

    def test_sets_source_and_date(self):
        adapter = StubAdapter()
        records = [{"name": "John"}]
        result = adapter.normalize(records)
        assert result[0]["source"] == "stub"
        assert "lastUpdated" in result[0]

    def test_preserves_existing_source(self):
        adapter = StubAdapter()
        records = [{"name": "John", "source": "custom"}]
        result = adapter.normalize(records)
        assert result[0]["source"] == "custom"


class TestGetContact:
    def test_default_returns_none(self):
        adapter = StubAdapter()
        assert adapter.get_contact() is None


class TestHtmlCaching:
    def test_html_initialized_to_none(self):
        adapter = StubAdapter()
        assert adapter._html is None

    def test_html_set_after_scrape(self):
        adapter = StubAdapter(html="<html>test</html>")
        adapter._test_members = [
            {"name": "John", "title": "Mayor", "email": "j@c.gov"}
        ]
        adapter.scrape()
        assert adapter._html == "<html>test</html>"
```

**Step 3: Run tests**

Run: `pytest tests/unit/test_state_helpers.py tests/unit/test_base_adapter.py -v`
Expected: All pass

**Step 4: Commit**

```bash
git add tests/unit/test_state_helpers.py tests/unit/test_base_adapter.py
git commit -m "test: add state helper and BaseAdapter contract tests"
```

---

### Task 4: Shared adapter tests — Revize

**Files:**
- Create: `tests/fixtures/html/revize_basic.html`
- Create: `tests/fixtures/html/revize_mayor.html`
- Create: `tests/fixtures/html/revize_cf_email.html`
- Create: `tests/unit/test_revize_parse.py`
- Reference: `scrapers/adapters/revize.py` (full file)

**Step 1: Create `tests/fixtures/html/revize_basic.html`**

Three members with standard bold name → mailto → phone pattern:

```html
<html><body>
<div class="fr-view">
  <strong>Alice Johnson</strong>
  <br>
  <a href="mailto:ajohnson@city.gov">ajohnson@city.gov</a>
  <br>
  (803) 555-0001
  <hr>
  <strong>Bob Williams</strong>
  <br>
  <a href="mailto:bwilliams@city.gov">bwilliams@city.gov</a>
  <br>
  <a href="tel:8035550002">(803) 555-0002</a>
  <hr>
  <strong>Carol Davis</strong>
  <br>
  <a href="mailto:cdavis@city.gov">cdavis@city.gov</a>
</div>
</body></html>
```

**Step 2: Create `tests/fixtures/html/revize_mayor.html`**

Mayor detection + Mayor Pro Tem suffix + generic email filtering + clerk exclusion:

```html
<html><body>
<div class="fr-view">
  <strong>Mayor John Smith</strong>
  <br>
  <a href="mailto:jsmith@city.gov">jsmith@city.gov</a>
  <br>
  (803) 555-1000
  <hr>
  <strong>Jane Doe, Mayor Pro Tem</strong>
  <br>
  <a href="mailto:jdoe@city.gov">jdoe@city.gov</a>
  <hr>
  <strong>Tom Brown</strong>
  <br>
  <a href="mailto:tbrown@city.gov">tbrown@city.gov</a>
  <hr>
  <a href="mailto:info@city.gov">info@city.gov</a>
  <hr>
  <strong>Sarah Clerk</strong>
  <br>
  <a href="mailto:clerk@city.gov">clerk@city.gov</a>
</div>
</body></html>
```

**Step 3: Create `tests/fixtures/html/revize_cf_email.html`**

Cloudflare email obfuscation:

```html
<html><body>
<div class="fr-view">
  <strong>Mike Wilson</strong>
  <br>
  <a href="/cdn-cgi/l/email-protection#PLACEHOLDER">
    <span class="__cf_email__" data-cfemail="PLACEHOLDER">[email protected]</span>
  </a>
</div>
</body></html>
```

Note: The `PLACEHOLDER` values will be computed in the test file using the XOR encoder from Task 2. We'll generate the fixture dynamically in the test instead of hardcoding hex.

**Step 4: Write `tests/unit/test_revize_parse.py`**

```python
"""Tests for RevizeAdapter.parse() with hand-crafted HTML fixtures."""

import pytest
from scrapers.adapters.base import deobfuscate_cf_email
from scrapers.adapters.revize import RevizeAdapter
from tests.conftest import load_fixture, make_adapter


class TestRevizeBasicParse:
    """Test basic name → email → phone extraction."""

    def test_extracts_three_members(self):
        html = load_fixture("revize_basic.html")
        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        assert len(members) == 3

    def test_member_names(self):
        html = load_fixture("revize_basic.html")
        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        names = [m["name"] for m in members]
        assert "Alice Johnson" in names
        assert "Bob Williams" in names
        assert "Carol Davis" in names

    def test_member_emails(self):
        html = load_fixture("revize_basic.html")
        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        emails = [m["email"] for m in members]
        assert "ajohnson@city.gov" in emails
        assert "bwilliams@city.gov" in emails
        assert "cdavis@city.gov" in emails

    def test_phone_from_text(self):
        html = load_fixture("revize_basic.html")
        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        alice = next(m for m in members if m["name"] == "Alice Johnson")
        assert alice["phone"] == "(803) 555-0001"

    def test_phone_from_tel_link(self):
        html = load_fixture("revize_basic.html")
        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        bob = next(m for m in members if m["name"] == "Bob Williams")
        assert bob["phone"] == "(803) 555-0002"

    def test_missing_phone_is_empty(self):
        html = load_fixture("revize_basic.html")
        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        carol = next(m for m in members if m["name"] == "Carol Davis")
        assert carol["phone"] == ""


class TestRevizeMayorDetection:
    """Test mayor title extraction and filtering."""

    def test_mayor_title_from_prefix(self):
        html = load_fixture("revize_mayor.html")
        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        john = next(m for m in members if "Smith" in m["name"])
        assert john["title"] == "Mayor"
        assert john["name"] == "John Smith"  # "Mayor" prefix stripped

    def test_mayor_pro_tem_from_suffix(self):
        html = load_fixture("revize_mayor.html")
        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        jane = next(m for m in members if "Doe" in m["name"])
        assert jane["title"] == "Mayor Pro Tem"
        assert jane["name"] == "Jane Doe"  # suffix stripped

    def test_generic_email_skipped(self):
        html = load_fixture("revize_mayor.html")
        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        emails = [m["email"] for m in members]
        assert "info@city.gov" not in emails

    def test_clerk_excluded_by_default(self):
        html = load_fixture("revize_mayor.html")
        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        names = [m["name"] for m in members]
        assert not any("Clerk" in n for n in names)


class TestRevizeCloudflareEmail:
    """Test Cloudflare email deobfuscation via data-cfemail."""

    def test_cf_email_decoded(self):
        # Build fixture HTML dynamically with a known encoded email
        email = "mwilson@city.gov"
        key = 0x5A
        encoded = format(key, "02x")
        for ch in email:
            encoded += format(ord(ch) ^ key, "02x")

        html = f"""<html><body>
        <div class="fr-view">
          <strong>Mike Wilson</strong>
          <br>
          <span class="__cf_email__" data-cfemail="{encoded}">[email protected]</span>
        </div>
        </body></html>"""

        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        assert len(members) == 1
        assert members[0]["email"] == "mwilson@city.gov"


class TestRevizeSeparators:
    """Test that <hr> prevents cross-pairing names with emails."""

    def test_hr_prevents_cross_pair(self):
        html = """<html><body>
        <div class="fr-view">
          <strong>Alice One</strong>
          <hr>
          <strong>Bob Two</strong>
          <a href="mailto:bob@city.gov">bob@city.gov</a>
        </div>
        </body></html>"""
        adapter = make_adapter(RevizeAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        # Alice has no email after <hr>, so should not be paired with Bob's email
        # Only Bob should appear (Alice has no email to pair with)
        assert len(members) == 1
        assert members[0]["name"] == "Bob Two"


class TestRevizeHelpers:
    """Test static helper methods on RevizeAdapter."""

    @pytest.mark.parametrize("text,expected", [
        ("John Smith", True),
        ("Alice Johnson-Williams", True),
        ("J", False),           # too short
        ("a lowercase name", False),  # doesn't start uppercase
        ("Click here for more info", False),  # contains excluded phrase
        ("http://example.com link", False),  # contains http
        ("john@city.gov", False),  # contains @
        ("123 Main Street Suite 200", False),  # too many digits
    ])
    def test_looks_like_name(self, text, expected):
        assert RevizeAdapter._looks_like_name(text) == expected

    @pytest.mark.parametrize("name,expected_name,expected_title", [
        ("Jane Doe, Mayor Pro Tem", "Jane Doe", "Mayor Pro Tem"),
        ("John Smith, Mayor", "John Smith", "Mayor"),
        ("Bob Brown, Councilman", "Bob Brown", ""),
        ("Alice Davis", "Alice Davis", ""),
    ])
    def test_strip_title_suffix(self, name, expected_name, expected_title):
        clean_name, title = RevizeAdapter._strip_title_suffix(name)
        assert clean_name == expected_name
        assert title == expected_title

    @pytest.mark.parametrize("email,expected", [
        ("info@city.gov", True),
        ("council@county.org", True),
        ("clerk@city.gov", True),
        ("jsmith@city.gov", False),
        ("mayor@town.gov", False),
    ])
    def test_is_generic_email(self, email, expected):
        assert RevizeAdapter._is_generic_email(email) == expected
```

**Step 5: Run tests**

Run: `pytest tests/unit/test_revize_parse.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add tests/fixtures/html/revize_basic.html tests/fixtures/html/revize_mayor.html tests/unit/test_revize_parse.py
git commit -m "test: add Revize adapter parse tests with HTML fixtures"
```

---

### Task 5: Shared adapter tests — CivicPlus

**Files:**
- Create: `tests/fixtures/html/civicplus_directory.html`
- Create: `tests/unit/test_civicplus_parse.py`
- Reference: `scrapers/adapters/civicplus.py` (full file)

**Step 1: Create `tests/fixtures/html/civicplus_directory.html`**

CivicPlus staff directory table with JS-obfuscated emails:

```html
<html><body>
<table id="cityDirectoryDepartmentDetails_1">
  <tr>
    <th>Name</th>
    <th>Title</th>
    <th>Email</th>
    <th>Phone</th>
  </tr>
  <tr>
    <td>Smith, John</td>
    <td>County Council Chairman</td>
    <td><script type="text/javascript">var w = "jsmith"; var x = "county.gov"; document.write('<a href="mailto:' + w + '@' + x + '">' + w + '@' + x + '</a>');</script></td>
    <td>(864) 596-2528</td>
  </tr>
  <tr>
    <td>Williams, Jane</td>
    <td>District 3 Representative</td>
    <td><script type="text/javascript">var w = "jwilliams"; var x = "county.gov"; document.write('<a href="mailto:' + w + '@' + x + '">' + w + '@' + x + '</a>');</script></td>
    <td>864-596-2529</td>
  </tr>
  <tr>
    <td>Brown, Alice</td>
    <td>Vice Chairman</td>
    <td><script type="text/javascript">var w = "abrown"; var x = "county.gov"; document.write('<a href="mailto:' + w + '@' + x + '">' + w + '@' + x + '</a>');</script></td>
    <td>864.596.2530</td>
  </tr>
  <tr>
    <td>Davis, Tom</td>
    <td>Clerk to County Council</td>
    <td><script type="text/javascript">var w = "tdavis"; var x = "county.gov"; document.write('<a href="mailto:' + w + '@' + x + '">' + w + '@' + x + '</a>');</script></td>
    <td>(864) 596-2531</td>
  </tr>
</table>
</body></html>
```

**Step 2: Write `tests/unit/test_civicplus_parse.py`**

```python
"""Tests for CivicPlusAdapter.parse() and helper methods."""

import pytest
from scrapers.adapters.civicplus import CivicPlusAdapter
from tests.conftest import load_fixture, make_adapter


class TestCivicPlusParse:
    """Test directory table parsing."""

    def _parse_fixture(self):
        html = load_fixture("civicplus_directory.html")
        adapter = make_adapter(CivicPlusAdapter, {
            "adapterConfig": {
                "baseUrl": "https://example.org",
                "councilPageId": "189",
                "directoryDeptId": "1",
            }
        })
        return adapter.parse(html)

    def test_extracts_three_members(self):
        members = self._parse_fixture()
        # 4 rows but Clerk should be excluded → 3 members
        assert len(members) == 3

    def test_clerk_excluded(self):
        members = self._parse_fixture()
        names = [m["name"] for m in members]
        assert "Tom Davis" not in names

    def test_name_flipped(self):
        members = self._parse_fixture()
        names = [m["name"] for m in members]
        assert "John Smith" in names  # was "Smith, John"
        assert "Jane Williams" in names

    def test_js_email_extracted(self):
        members = self._parse_fixture()
        john = next(m for m in members if m["name"] == "John Smith")
        assert john["email"] == "jsmith@county.gov"

    def test_title_normalized_chairman(self):
        members = self._parse_fixture()
        john = next(m for m in members if m["name"] == "John Smith")
        assert john["title"] == "Chairman"

    def test_title_normalized_district(self):
        members = self._parse_fixture()
        jane = next(m for m in members if m["name"] == "Jane Williams")
        assert jane["title"] == "Council Member, District 3"

    def test_title_normalized_vice(self):
        members = self._parse_fixture()
        alice = next(m for m in members if m["name"] == "Alice Brown")
        assert alice["title"] == "Vice Chairman"

    def test_phone_formatted(self):
        members = self._parse_fixture()
        john = next(m for m in members if m["name"] == "John Smith")
        assert john["phone"] == "(864) 596-2528"


class TestCivicPlusHelpers:

    @pytest.mark.parametrize("name_raw,expected", [
        ("Smith, John", "John Smith"),
        ("Lynch, A. Manning", "A. Manning Lynch"),
        ("John Smith", "John Smith"),  # no comma → unchanged
        ("  Smith , John  ", "John Smith"),
    ])
    def test_flip_name(self, name_raw, expected):
        assert CivicPlusAdapter._flip_name(name_raw) == expected

    @pytest.mark.parametrize("title_raw,expected", [
        ("District 3 Representative", "Council Member, District 3"),
        ("County Council Chairman", "Chairman"),
        ("Vice Chairman", "Vice Chairman"),
        ("At-Large Member", "Council Member, At Large"),
        ("Council Member", "Council Member"),
    ])
    def test_normalize_title(self, title_raw, expected):
        assert CivicPlusAdapter._normalize_title(title_raw) == expected

    @pytest.mark.parametrize("title,exclude,expected", [
        ("Clerk to Council", ["clerk"], True),
        ("Council Member", ["clerk"], False),
        ("County Administrator", ["administrator"], True),
    ])
    def test_should_exclude(self, title, exclude, expected):
        assert CivicPlusAdapter._should_exclude(title, exclude) == expected

    def test_discover_directory_id(self):
        html = '<a href="/directory.aspx?did=42">Staff Directory</a>'
        assert CivicPlusAdapter._discover_directory_id(html) == "42"

    def test_discover_directory_id_not_found(self):
        assert CivicPlusAdapter._discover_directory_id("<html></html>") == ""

    def test_extract_email_from_js(self):
        from bs4 import BeautifulSoup
        html = '<td><script type="text/javascript">var w = "test"; var x = "city.gov";</script></td>'
        soup = BeautifulSoup(html, "html.parser")
        cell = soup.find("td")
        assert CivicPlusAdapter._extract_email(cell) == "test@city.gov"

    def test_extract_email_fallback_mailto(self):
        from bs4 import BeautifulSoup
        html = '<td><a href="mailto:test@city.gov">test@city.gov</a></td>'
        soup = BeautifulSoup(html, "html.parser")
        cell = soup.find("td")
        assert CivicPlusAdapter._extract_email(cell) == "test@city.gov"

    def test_extract_email_empty(self):
        from bs4 import BeautifulSoup
        html = '<td>No email</td>'
        soup = BeautifulSoup(html, "html.parser")
        cell = soup.find("td")
        assert CivicPlusAdapter._extract_email(cell) == ""
```

**Step 3: Run tests**

Run: `pytest tests/unit/test_civicplus_parse.py -v`
Expected: All pass

**Step 4: Commit**

```bash
git add tests/fixtures/html/civicplus_directory.html tests/unit/test_civicplus_parse.py
git commit -m "test: add CivicPlus adapter parse tests"
```

---

### Task 6: Shared adapter tests — TableAdapter and DrupalViews

**Files:**
- Create: `tests/fixtures/html/table_basic.html`
- Create: `tests/fixtures/html/drupal_views_row.html`
- Create: `tests/fixtures/html/drupal_person_item.html`
- Create: `tests/unit/test_table_adapter.py`
- Create: `tests/unit/test_drupal_views.py`
- Reference: `scrapers/adapters/table_adapter.py`, `scrapers/adapters/drupal_views.py`

**Step 1: Create `tests/fixtures/html/table_basic.html`**

```html
<html><body>
<table>
  <tr>
    <th>Name</th>
    <th>Title</th>
    <th>District</th>
    <th>Email</th>
    <th>Phone</th>
  </tr>
  <tr>
    <td>Smith, John</td>
    <td>Chairman</td>
    <td>1</td>
    <td><a href="mailto:jsmith@county.gov">jsmith@county.gov</a></td>
    <td>(803) 555-0001</td>
  </tr>
  <tr>
    <td>Jane Williams</td>
    <td>Council Member</td>
    <td>2</td>
    <td>jwilliams@county.gov</td>
    <td>(803) 555-0002</td>
  </tr>
  <tr>
    <td>Mr. Bob Brown</td>
    <td>District 3</td>
    <td></td>
    <td><a href="mailto:bbrown@county.gov">bbrown@county.gov</a></td>
    <td>(803) 555-0003</td>
  </tr>
</table>
</body></html>
```

**Step 2: Create `tests/fixtures/html/drupal_views_row.html`**

```html
<html><body>
<div class="views-row">
  <div class="views-field-title"><a href="/member/1">Alice Johnson</a></div>
  <div class="views-field-field-district">District 1</div>
  <div class="views-field-field-job-title">Chairman</div>
  <div class="views-field-field-email-address"><a href="mailto:ajohnson@county.gov">ajohnson@county.gov</a></div>
  <div class="views-field-field-phone-numbers"><a href="tel:8035550001">(803) 555-0001</a></div>
</div>
<div class="views-row">
  <div class="views-field-title">Bob Williams</div>
  <div class="views-field-field-district">District 2</div>
  <div class="views-field-field-job-title">Councilman</div>
  <div class="views-field-field-email-address">bwilliams@county.gov</div>
  <div class="views-field-field-phone-numbers">(803) 555-0002</div>
</div>
</body></html>
```

**Step 3: Create `tests/fixtures/html/drupal_person_item.html`**

```html
<html><body>
<article class="person-item">
  <div class="person-item__title"><a href="/member/1">Carol Davis</a></div>
  <div class="person-item__job-title">Mayor</div>
  <div class="person-item__email-address"><a href="mailto:cdavis@city.gov">cdavis@city.gov</a></div>
  <div class="person-item__phone-numbers"><a href="tel:8035550010">(803) 555-0010</a></div>
</article>
<article class="person-item">
  <div class="person-item__title">Dan Evans</div>
  <div class="person-item__job-title">Council Member</div>
  <div class="person-item__email-address">devans@city.gov</div>
  <div class="person-item__phone-numbers">(803) 555-0011</div>
</article>
</body></html>
```

**Step 4: Write `tests/unit/test_table_adapter.py`**

```python
"""Tests for TableAdapter.parse() with hand-crafted HTML fixtures."""

import pytest
from scrapers.adapters.table_adapter import TableAdapter
from tests.conftest import load_fixture, make_adapter


class TestTableAdapterParse:

    def _parse_fixture(self):
        html = load_fixture("table_basic.html")
        adapter = make_adapter(TableAdapter, {"url": "https://example.com"})
        return adapter.parse(html)

    def test_extracts_three_members(self):
        members = self._parse_fixture()
        assert len(members) == 3

    def test_name_reversed_from_last_first(self):
        members = self._parse_fixture()
        names = [m["name"] for m in members]
        assert "John Smith" in names

    def test_name_without_comma_unchanged(self):
        members = self._parse_fixture()
        names = [m["name"] for m in members]
        assert "Jane Williams" in names

    def test_honorific_stripped(self):
        members = self._parse_fixture()
        names = [m["name"] for m in members]
        assert "Bob Brown" in names  # "Mr." stripped

    def test_district_column_applied(self):
        members = self._parse_fixture()
        jane = next(m for m in members if m["name"] == "Jane Williams")
        assert jane["title"] == "Council Member, District 2"

    def test_district_only_title_expanded(self):
        members = self._parse_fixture()
        bob = next(m for m in members if m["name"] == "Bob Brown")
        assert "District 3" in bob["title"]

    def test_email_from_mailto_link(self):
        members = self._parse_fixture()
        john = next(m for m in members if m["name"] == "John Smith")
        assert john["email"] == "jsmith@county.gov"

    def test_email_from_text(self):
        members = self._parse_fixture()
        jane = next(m for m in members if m["name"] == "Jane Williams")
        assert jane["email"] == "jwilliams@county.gov"

    def test_phone_extracted(self):
        members = self._parse_fixture()
        john = next(m for m in members if m["name"] == "John Smith")
        assert john["phone"] == "(803) 555-0001"


class TestTableAdapterColumnDetection:

    def test_detects_standard_headers(self):
        from bs4 import BeautifulSoup
        html = "<table><tr><th>Name</th><th>Title</th><th>Email</th><th>Phone</th></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        headers = soup.find_all("th")
        adapter = make_adapter(TableAdapter, {"url": "https://example.com"})
        col_map = adapter._detect_columns(headers)
        assert col_map["name"] == 0
        assert col_map["title"] == 1
        assert col_map["email"] == 2
        assert col_map["phone"] == 3

    def test_detects_alternate_header_text(self):
        from bs4 import BeautifulSoup
        html = "<table><tr><th>Member</th><th>Position</th><th>E-Mail</th><th>Telephone</th></tr></table>"
        soup = BeautifulSoup(html, "html.parser")
        headers = soup.find_all("th")
        adapter = make_adapter(TableAdapter, {"url": "https://example.com"})
        col_map = adapter._detect_columns(headers)
        assert "name" in col_map
        assert "title" in col_map
        assert "email" in col_map
        assert "phone" in col_map
```

**Step 5: Write `tests/unit/test_drupal_views.py`**

```python
"""Tests for DrupalViewsAdapter.parse() with both Drupal patterns."""

import pytest
from scrapers.adapters.drupal_views import DrupalViewsAdapter
from tests.conftest import load_fixture, make_adapter


class TestDrupalViewsRowPattern:

    def _parse_fixture(self):
        html = load_fixture("drupal_views_row.html")
        adapter = make_adapter(DrupalViewsAdapter, {"url": "https://example.com"})
        return adapter.parse(html)

    def test_extracts_two_members(self):
        members = self._parse_fixture()
        assert len(members) == 2

    def test_name_from_link(self):
        members = self._parse_fixture()
        names = [m["name"] for m in members]
        assert "Alice Johnson" in names

    def test_name_from_text(self):
        members = self._parse_fixture()
        names = [m["name"] for m in members]
        assert "Bob Williams" in names

    def test_title_with_district(self):
        members = self._parse_fixture()
        alice = next(m for m in members if m["name"] == "Alice Johnson")
        assert alice["title"] == "Chairman, District 1"

    def test_email_from_mailto(self):
        members = self._parse_fixture()
        alice = next(m for m in members if m["name"] == "Alice Johnson")
        assert alice["email"] == "ajohnson@county.gov"

    def test_email_from_text(self):
        members = self._parse_fixture()
        bob = next(m for m in members if m["name"] == "Bob Williams")
        assert bob["email"] == "bwilliams@county.gov"

    def test_phone_from_tel_link(self):
        members = self._parse_fixture()
        alice = next(m for m in members if m["name"] == "Alice Johnson")
        assert alice["phone"] == "(803) 555-0001"


class TestDrupalPersonItemPattern:

    def _parse_fixture(self):
        html = load_fixture("drupal_person_item.html")
        adapter = make_adapter(DrupalViewsAdapter, {"url": "https://example.com"})
        return adapter.parse(html)

    def test_extracts_two_members(self):
        members = self._parse_fixture()
        assert len(members) == 2

    def test_mayor_title(self):
        members = self._parse_fixture()
        carol = next(m for m in members if m["name"] == "Carol Davis")
        assert carol["title"] == "Mayor"

    def test_email_extraction(self):
        members = self._parse_fixture()
        carol = next(m for m in members if m["name"] == "Carol Davis")
        assert carol["email"] == "cdavis@city.gov"


class TestDrupalNormalizeTitle:

    @pytest.mark.parametrize("raw,district,expected", [
        ("Mayor", "", "Mayor"),
        ("Mayor Pro Tem", "", "Mayor Pro Tem"),
        ("Mayor Pro Tem", "3", "Mayor Pro Tem, District 3"),
        ("Chairman", "", "Chairman"),
        ("Chairman", "1", "Chairman, District 1"),
        ("Vice Chairman", "", "Vice Chairman"),
        ("Vice Chairman", "5", "Vice Chairman, District 5"),
        ("Seat #4 Western", "", "Council Member, Seat 4"),
        ("", "2", "Council Member, District 2"),
        ("", "", "Council Member"),
        ("District 7 Councilman", "", "Council Member, District 7"),
    ])
    def test_normalize_title(self, raw, district, expected):
        assert DrupalViewsAdapter._normalize_title(raw, district) == expected
```

**Step 6: Run tests**

Run: `pytest tests/unit/test_table_adapter.py tests/unit/test_drupal_views.py -v`
Expected: All pass

**Step 7: Commit**

```bash
git add tests/fixtures/html/table_basic.html tests/fixtures/html/drupal_views_row.html tests/fixtures/html/drupal_person_item.html tests/unit/test_table_adapter.py tests/unit/test_drupal_views.py
git commit -m "test: add TableAdapter and DrupalViews parse tests"
```

---

### Task 7: Shared adapter tests — GenericMailto

**Files:**
- Create: `tests/fixtures/html/generic_mailto.html`
- Create: `tests/unit/test_generic_mailto.py`
- Reference: `scrapers/adapters/generic_mailto.py`

**Step 1: Create `tests/fixtures/html/generic_mailto.html`**

WordPress-style content with `entry-content` container:

```html
<html><body>
<div class="entry-content">
  <h3>Alice Mayor</h3>
  <strong>Mayor Alice Johnson</strong>
  <a href="mailto:ajohnson@city.gov">ajohnson@city.gov</a>
  <a href="tel:8035550001">(803) 555-0001</a>
  <hr>
  <strong>Bob Williams</strong>
  <a href="mailto:bwilliams@city.gov">bwilliams@city.gov</a>
  <hr>
  <strong>Carol Davis</strong>
  <a href="mailto:cdavis@city.gov">cdavis@city.gov</a>
</div>
</body></html>
```

**Step 2: Write `tests/unit/test_generic_mailto.py`**

```python
"""Tests for GenericMailtoAdapter.parse() content area detection."""

import pytest
from scrapers.adapters.generic_mailto import GenericMailtoAdapter
from tests.conftest import load_fixture, make_adapter


class TestGenericMailtoParse:

    def test_finds_entry_content(self):
        html = load_fixture("generic_mailto.html")
        adapter = make_adapter(GenericMailtoAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        assert len(members) >= 2

    def test_extracts_emails(self):
        html = load_fixture("generic_mailto.html")
        adapter = make_adapter(GenericMailtoAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        emails = [m["email"] for m in members]
        assert "bwilliams@city.gov" in emails
        assert "cdavis@city.gov" in emails


class TestGenericMailtoContentDetection:

    def test_finds_et_pb_section(self):
        html = """<html><body>
        <div class="et_pb_section">
          <strong>John Smith</strong>
          <a href="mailto:js@city.gov">js@city.gov</a>
        </div>
        </body></html>"""
        adapter = make_adapter(GenericMailtoAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        assert len(members) == 1

    def test_finds_node_content(self):
        html = """<html><body>
        <div class="node__content">
          <strong>John Smith</strong>
          <a href="mailto:js@city.gov">js@city.gov</a>
        </div>
        </body></html>"""
        adapter = make_adapter(GenericMailtoAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        assert len(members) == 1

    def test_custom_content_selector(self):
        html = """<html><body>
        <div id="my-custom-area">
          <strong>John Smith</strong>
          <a href="mailto:js@city.gov">js@city.gov</a>
        </div>
        </body></html>"""
        adapter = make_adapter(GenericMailtoAdapter, {
            "url": "https://example.com",
            "adapterConfig": {"contentSelector": "#my-custom-area"},
        })
        members = adapter.parse(html)
        assert len(members) == 1

    def test_falls_through_to_body(self):
        html = """<html><body>
          <strong>John Smith</strong>
          <a href="mailto:js@city.gov">js@city.gov</a>
        </body></html>"""
        adapter = make_adapter(GenericMailtoAdapter, {"url": "https://example.com"})
        members = adapter.parse(html)
        assert len(members) == 1
```

**Step 3: Run tests**

Run: `pytest tests/unit/test_generic_mailto.py -v`
Expected: All pass

**Step 4: Commit**

```bash
git add tests/fixtures/html/generic_mailto.html tests/unit/test_generic_mailto.py
git commit -m "test: add GenericMailto adapter parse tests"
```

---

### Task 8: Script and validation tests

**Files:**
- Create: `tests/unit/test_quality_report.py`
- Create: `tests/unit/test_stale_check.py`
- Create: `tests/unit/test_validate.py`
- Reference: `scripts/quality_report.py`, `scripts/stale_check.py`, `validate.py`

**Step 1: Write `tests/unit/test_quality_report.py`**

```python
"""Tests for quality report pure functions."""

import json
import os
import pytest

# The script uses ROOT_DIR-relative paths; we test the pure functions directly
from scripts.quality_report import (
    check_executive,
    check_contact,
    _has_title_match,
    format_summary,
    analyze_local_file,
)


class TestCheckExecutive:

    def test_finds_mayor_in_place(self):
        members = [
            {"name": "John", "title": "Mayor"},
            {"name": "Jane", "title": "Council Member, District 1"},
        ]
        assert check_executive(members, "place") == "Mayor"

    def test_finds_chairman_in_county(self):
        members = [
            {"name": "John", "title": "Chairman, District 1"},
            {"name": "Jane", "title": "Council Member, District 2"},
        ]
        assert check_executive(members, "county") == "Chairman"

    def test_skips_vice_chairman(self):
        members = [
            {"name": "John", "title": "Vice Chairman, District 1"},
        ]
        assert check_executive(members, "county") is None

    def test_empty_list(self):
        assert check_executive([], "place") is None

    def test_no_executive_title(self):
        members = [{"name": "John", "title": "Council Member"}]
        assert check_executive(members, "place") is None


class TestCheckContact:

    def test_valid_contact(self):
        meta = {"contact": {"phone": "(803) 555-1234", "email": "", "label": "City Hall"}}
        result = check_contact(meta)
        assert result is not None
        assert "(803) 555-1234" in result

    def test_empty_contact(self):
        meta = {"contact": {}}
        assert check_contact(meta) is None

    def test_no_contact_key(self):
        meta = {}
        assert check_contact(meta) is None

    def test_contact_not_dict(self):
        meta = {"contact": "phone"}
        assert check_contact(meta) is None


class TestHasTitleMatch:

    def test_mayor_matches(self):
        assert _has_title_match("mayor", {"mayor"}) is True

    def test_vice_mayor_does_not_match(self):
        assert _has_title_match("vice mayor", {"mayor"}) is False

    def test_deputy_chair_does_not_match(self):
        assert _has_title_match("deputy chairman", {"chairman"}) is False

    def test_chairman_matches(self):
        assert _has_title_match("chairman, district 1", {"chairman"}) is True


class TestFormatSummary:

    def test_format_with_known_data(self):
        local = [
            {"has_email": True, "has_phone": True, "executive": "Mayor", "contact": None, "members": 5},
            {"has_email": False, "has_phone": True, "executive": None, "contact": "(803) 555-0000", "members": 3},
            {"has_email": False, "has_phone": False, "executive": None, "contact": None, "members": 0},
        ]
        state = [{"state": "SC", "legislators": 170, "has_executive": True}]
        result = format_summary(local, state)
        assert "3 jurisdictions" in result
        assert "1 with email" in result
        assert "2 with phone" in result
        assert "1 with executive" in result
        assert "1 with 0 members" in result
        assert "SC state: 170 legislators" in result


class TestAnalyzeLocalFile:

    def test_analyzes_valid_file(self, tmp_path):
        data = {
            "meta": {
                "state": "SC",
                "level": "local",
                "jurisdiction": "place:test",
                "label": "Test City",
                "lastUpdated": "2026-03-14",
                "adapter": "test",
            },
            "members": [
                {"name": "John", "title": "Mayor", "email": "j@c.gov", "phone": ""},
                {"name": "Jane", "title": "Council Member", "email": "", "phone": "(803) 555-1234"},
            ],
        }
        filepath = tmp_path / "place-test.json"
        filepath.write_text(json.dumps(data))
        result = analyze_local_file(str(filepath))
        assert result is not None
        assert result["members"] == 2
        assert result["has_email"] is True
        assert result["has_phone"] is True
        assert result["executive"] == "Mayor"

    def test_returns_none_for_invalid_json(self, tmp_path):
        filepath = tmp_path / "bad.json"
        filepath.write_text("not json")
        assert analyze_local_file(str(filepath)) is None
```

**Step 2: Write `tests/unit/test_stale_check.py`**

```python
"""Tests for stale data detection logic."""

import json
import os
from datetime import date, timedelta
import pytest


def find_stale_files(data_dir, threshold_days):
    """Extract the stale detection logic from stale_check.py main().

    This mirrors the logic in scripts/stale_check.py but accepts a
    custom data_dir instead of using the hardcoded DATA_DIR.
    """
    cutoff = date.today() - timedelta(days=threshold_days)
    stale = []

    for state_code in sorted(os.listdir(data_dir)):
        local_dir = os.path.join(data_dir, state_code, "local")
        if not os.path.isdir(local_dir):
            continue

        for filename in sorted(os.listdir(local_dir)):
            if not filename.endswith(".json"):
                continue

            filepath = os.path.join(local_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError):
                continue

            meta = data.get("meta", {})
            last_changed = meta.get("dataLastChanged", meta.get("lastUpdated", ""))
            if not last_changed:
                continue

            try:
                last_date = date.fromisoformat(last_changed)
            except ValueError:
                continue

            if last_date < cutoff:
                stale.append({
                    "jurisdiction": meta.get("jurisdiction", filename),
                    "dataLastChanged": last_changed,
                    "daysSinceChange": (date.today() - last_date).days,
                })

    return stale


def _write_local_json(local_dir, filename, days_ago=None, use_last_updated=False, date_str=None):
    """Helper to write a test JSON file with a specific age."""
    if date_str is None and days_ago is not None:
        date_str = (date.today() - timedelta(days=days_ago)).isoformat()

    meta = {
        "state": "SC",
        "jurisdiction": filename.replace(".json", ""),
        "label": "Test",
    }
    if date_str:
        if use_last_updated:
            meta["lastUpdated"] = date_str
        else:
            meta["dataLastChanged"] = date_str

    data = {"meta": meta, "members": []}
    filepath = os.path.join(local_dir, filename)
    with open(filepath, "w") as f:
        json.dump(data, f)


class TestStaleDetection:

    def test_flags_old_file(self, tmp_path):
        state_dir = tmp_path / "sc" / "local"
        state_dir.mkdir(parents=True)
        _write_local_json(str(state_dir), "place-old.json", days_ago=100)
        _write_local_json(str(state_dir), "place-recent.json", days_ago=50)
        _write_local_json(str(state_dir), "place-today.json", days_ago=0)

        stale = find_stale_files(str(tmp_path), threshold_days=90)
        assert len(stale) == 1
        assert stale[0]["jurisdiction"] == "place-old"

    def test_falls_back_to_last_updated(self, tmp_path):
        state_dir = tmp_path / "sc" / "local"
        state_dir.mkdir(parents=True)
        _write_local_json(str(state_dir), "place-fallback.json",
                          days_ago=100, use_last_updated=True)

        stale = find_stale_files(str(tmp_path), threshold_days=90)
        assert len(stale) == 1

    def test_skips_invalid_date(self, tmp_path):
        state_dir = tmp_path / "sc" / "local"
        state_dir.mkdir(parents=True)
        _write_local_json(str(state_dir), "place-bad.json", date_str="not-a-date")

        stale = find_stale_files(str(tmp_path), threshold_days=90)
        assert len(stale) == 0

    def test_skips_missing_date(self, tmp_path):
        state_dir = tmp_path / "sc" / "local"
        state_dir.mkdir(parents=True)
        _write_local_json(str(state_dir), "place-nodate.json")

        stale = find_stale_files(str(tmp_path), threshold_days=90)
        assert len(stale) == 0

    def test_empty_directory(self, tmp_path):
        stale = find_stale_files(str(tmp_path), threshold_days=90)
        assert len(stale) == 0
```

**Step 3: Write `tests/unit/test_validate.py`**

```python
"""Tests for validate.py validator functions."""

import pytest
import validate as val


@pytest.fixture(autouse=True)
def clear_validation_state():
    """Reset the module-level error/warning lists between tests."""
    val.errors.clear()
    val.warnings.clear()
    yield
    val.errors.clear()
    val.warnings.clear()


class TestValidateLocalFile:

    def _valid_local_data(self):
        return {
            "meta": {
                "state": "SC",
                "level": "local",
                "jurisdiction": "place:test",
                "label": "Test City",
                "lastUpdated": "2026-03-14",
                "adapter": "test",
            },
            "members": [
                {"name": "John", "title": "Mayor", "email": "j@c.gov", "phone": "(803) 555-1234"},
            ],
        }

    def test_valid_data_no_errors(self):
        val.validate_local_file(self._valid_local_data(), "test.json")
        assert len(val.errors) == 0

    def test_missing_meta_is_error(self):
        data = {"members": []}
        val.validate_local_file(data, "test.json")
        assert any("meta" in e for e in val.errors)

    def test_missing_members_is_error(self):
        data = self._valid_local_data()
        data["members"] = "not a list"
        val.validate_local_file(data, "test.json")
        assert any("members" in e for e in val.errors)

    def test_empty_members_is_warning(self):
        data = self._valid_local_data()
        data["members"] = []
        val.validate_local_file(data, "test.json")
        assert any("0 members" in w for w in val.warnings)

    def test_admin_title_is_warning(self):
        data = self._valid_local_data()
        data["members"] = [
            {"name": "Jane", "title": "Clerk to Council", "email": "j@c.gov"},
        ]
        val.validate_local_file(data, "test.json")
        assert any("admin staff" in w for w in val.warnings)

    def test_bad_phone_format_is_warning(self):
        data = self._valid_local_data()
        data["members"][0]["phone"] = "555-1234"
        val.validate_local_file(data, "test.json")
        assert any("phone format" in w for w in val.warnings)

    def test_valid_contact_no_errors(self):
        data = self._valid_local_data()
        data["meta"]["contact"] = {
            "phone": "(803) 555-0000",
            "email": "",
            "note": "City Hall",
        }
        val.validate_local_file(data, "test.json")
        assert len(val.errors) == 0

    def test_bad_contact_phone_is_warning(self):
        data = self._valid_local_data()
        data["meta"]["contact"] = {"phone": "555-0000"}
        val.validate_local_file(data, "test.json")
        assert any("contact.phone" in w for w in val.warnings)


class TestValidateStateJson:

    def _valid_state_data(self):
        senate = {str(i): {"name": f"Senator {i}", "district": str(i),
                           "party": "R", "email": f"s{i}@state.gov"}
                  for i in range(1, 47)}
        house = {str(i): {"name": f"Rep {i}", "district": str(i),
                          "party": "D", "email": f"r{i}@state.gov"}
                 for i in range(1, 125)}
        return {
            "meta": {
                "state": "SC",
                "level": "state",
                "lastUpdated": "2026-03-14",
                "source": "openstates",
            },
            "senate": senate,
            "house": house,
        }

    def test_valid_data_no_errors(self):
        val.validate_state_json(self._valid_state_data(), "SC", "state.json")
        assert len(val.errors) == 0

    def test_detects_senate_drop(self):
        data = self._valid_state_data()
        # Keep only 10 senators (below 50% of 46)
        data["senate"] = {str(i): data["senate"][str(i)] for i in range(1, 11)}
        val.validate_state_json(data, "SC", "state.json")
        assert any("drop" in e.lower() for e in val.errors)

    def test_bad_email_format_is_warning(self):
        data = self._valid_state_data()
        data["senate"]["1"]["email"] = "not-an-email"
        val.validate_state_json(data, "SC", "state.json")
        assert any("email format" in w for w in val.warnings)

    def test_valid_executive_no_errors(self):
        data = self._valid_state_data()
        data["executive"] = [
            {"name": "Henry McMaster", "title": "Governor",
             "email": "gov@sc.gov", "phone": "(803) 734-2100"},
        ]
        val.validate_state_json(data, "SC", "state.json")
        assert not any("executive" in e for e in val.errors)

    def test_executive_missing_name_is_error(self):
        data = self._valid_state_data()
        data["executive"] = [{"title": "Governor"}]
        val.validate_state_json(data, "SC", "state.json")
        assert any("executive" in e and "name" in e for e in val.errors)

    def test_executive_not_list_is_error(self):
        data = self._valid_state_data()
        data["executive"] = {"governor": "Henry McMaster"}
        val.validate_state_json(data, "SC", "state.json")
        assert any("executive" in e and "list" in e for e in val.errors)
```

**Step 4: Run all tests**

Run: `pytest tests/unit/ -v`
Expected: All pass

**Step 5: Commit**

```bash
git add tests/unit/test_quality_report.py tests/unit/test_stale_check.py tests/unit/test_validate.py
git commit -m "test: add quality report, stale check, and validation tests"
```

---

### Task 9: Integration tests — real HTML snapshots

**Files:**
- Create: `tests/fixtures/snapshots/snapshots.json`
- Create: `tests/fixtures/snapshots/README.md`
- Create: `scripts/refresh_snapshots.py`
- Create: `tests/integration/test_real_snapshots.py`
- Create saved HTML files (via refresh script)

**Step 1: Create `tests/fixtures/snapshots/snapshots.json`**

```json
{
  "snapshots": [
    {
      "file": "revize_walterboro.html",
      "url": "https://www.walterborosc.org/city-council",
      "adapter": "revize",
      "adapter_module": "scrapers.adapters.revize",
      "adapter_class": "RevizeAdapter",
      "entry": {"id": "place:walterboro", "url": "https://www.walterborosc.org/city-council"},
      "min_members": 3
    },
    {
      "file": "table_calhoun.html",
      "url": "https://calhouncounty.sc.gov/officials",
      "adapter": "table",
      "adapter_module": "scrapers.adapters.table_adapter",
      "adapter_class": "TableAdapter",
      "entry": {"id": "county:calhoun", "url": "https://calhouncounty.sc.gov/officials"},
      "min_members": 3
    },
    {
      "file": "generic_mailto_camden.html",
      "url": "https://www.experiencecamdensc.com/government/mayor-and-city-council/",
      "adapter": "generic_mailto",
      "adapter_module": "scrapers.adapters.generic_mailto",
      "adapter_class": "GenericMailtoAdapter",
      "entry": {"id": "place:camden", "url": "https://www.experiencecamdensc.com/government/mayor-and-city-council/"},
      "min_members": 3
    }
  ]
}
```

Note: CivicPlus and DrupalViews require multi-step fetch (directory ID discovery, views-row detection) that makes snapshot testing harder. Start with the three adapters above that have simple single-page parse. Add more later.

**Step 2: Create `scripts/refresh_snapshots.py`**

```python
"""Fetch fresh HTML snapshots for integration tests.

Usage:
    python scripts/refresh_snapshots.py

Reads tests/fixtures/snapshots/snapshots.json and saves each URL's HTML
to the corresponding file in tests/fixtures/snapshots/.
"""

import json
import os

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SNAPSHOTS_DIR = os.path.join(PROJECT_ROOT, "tests", "fixtures", "snapshots")
MANIFEST_PATH = os.path.join(SNAPSHOTS_DIR, "snapshots.json")
USER_AGENT = "OpenCivics/1.0 (+https://github.com/TimSimpsonJr/open-civics)"


def main():
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)

    for entry in manifest["snapshots"]:
        url = entry["url"]
        filename = entry["file"]
        filepath = os.path.join(SNAPSHOTS_DIR, filename)

        print(f"Fetching {url} -> {filename}...")
        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
            resp.raise_for_status()
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(resp.text)
            print(f"  Saved ({len(resp.text)} bytes)")
        except Exception as e:
            print(f"  FAILED: {e}")

    print("\nDone. Remember to commit updated snapshots.")


if __name__ == "__main__":
    main()
```

**Step 3: Create `tests/fixtures/snapshots/README.md`**

```markdown
# Test Snapshots

Saved HTML from real sites for integration smoke tests.

## Refreshing

Run from the project root:

    python scripts/refresh_snapshots.py

This fetches each URL listed in `snapshots.json` and saves the HTML here.
Commit the updated files after refreshing.

## Adding a new snapshot

1. Add an entry to `snapshots.json` with the URL, adapter class, and minimum member count
2. Run `python scripts/refresh_snapshots.py`
3. Commit the new HTML file
```

**Step 4: Run the refresh script to save initial snapshots**

Run: `python scripts/refresh_snapshots.py`
Expected: 3 HTML files saved to `tests/fixtures/snapshots/`

**Step 5: Write `tests/integration/test_real_snapshots.py`**

```python
"""Integration smoke tests using real saved HTML from live sites.

These tests verify that shared adapters can parse actual site HTML
without errors and produce reasonable output. They do NOT verify
exact member names (which change over time).

Run with: pytest tests/integration/ -v
Skip with: pytest -m "not integration"
"""

import importlib
import json
import os

import pytest

SNAPSHOTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "fixtures", "snapshots"
)
MANIFEST_PATH = os.path.join(SNAPSHOTS_DIR, "snapshots.json")


def _load_manifest():
    if not os.path.exists(MANIFEST_PATH):
        return []
    with open(MANIFEST_PATH, "r") as f:
        data = json.load(f)
    return data.get("snapshots", [])


def _snapshot_ids():
    """Generate test IDs from manifest for parametrize."""
    return [s["file"].replace(".html", "") for s in _load_manifest()]


def _load_snapshots():
    """Load all snapshot configs for parametrize."""
    return _load_manifest()


@pytest.mark.integration
@pytest.mark.parametrize("snapshot", _load_snapshots(), ids=_snapshot_ids())
def test_snapshot_parse(snapshot):
    """Verify adapter produces reasonable output from real HTML."""
    filepath = os.path.join(SNAPSHOTS_DIR, snapshot["file"])
    if not os.path.exists(filepath):
        pytest.skip(f"Snapshot file not found: {snapshot['file']}")

    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    # Import the adapter class
    module = importlib.import_module(snapshot["adapter_module"])
    adapter_class = getattr(module, snapshot["adapter_class"])

    # Build entry dict
    entry = {
        "id": snapshot["entry"].get("id", "test"),
        "name": "Snapshot Test",
        "type": "place",
        "county": "Test",
        "url": snapshot["entry"].get("url", ""),
        "adapterConfig": snapshot["entry"].get("adapterConfig", {}),
    }

    adapter = adapter_class(entry)
    members = adapter.parse(html)

    # Basic sanity checks
    min_members = snapshot.get("min_members", 1)
    assert len(members) >= min_members, (
        f"Expected at least {min_members} members, got {len(members)}"
    )

    for i, member in enumerate(members):
        assert member.get("name"), f"Member {i} has no name"
        assert isinstance(member.get("title", ""), str)
```

**Step 6: Run integration tests**

Run: `pytest tests/integration/ -v`
Expected: All 3 snapshot tests pass (assuming snapshots were saved successfully)

**Step 7: Run full test suite**

Run: `pytest -v`
Expected: All unit + integration tests pass

**Step 8: Commit**

```bash
git add tests/fixtures/snapshots/ scripts/refresh_snapshots.py tests/integration/test_real_snapshots.py
git commit -m "test: add integration tests with real site HTML snapshots"
```

---

### Task 10: Final cleanup — update CLAUDE.md, MANIFEST.md, validate CI

**Files:**
- Modify: `CLAUDE.md` — add test commands
- Modify: `MANIFEST.md` — add tests directory
- Modify: `.github/workflows/validate.yml` — add test step

**Step 1: Add test commands to `CLAUDE.md`**

Add after the existing commands section:

```markdown
- `pytest tests/unit/ -v` — run unit tests (fast)
- `pytest -v` — run all tests including integration
- `python scripts/refresh_snapshots.py` — refresh integration test HTML snapshots
```

**Step 2: Update `MANIFEST.md`**

Add the `tests/` directory to the structure section and update key relationships.

**Step 3: Add pytest to validate.yml**

Add a test step before the validation step in `.github/workflows/validate.yml`:

```yaml
      - run: pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest tests/unit/ -v
```

This ensures unit tests run on every PR that touches data or code.

**Step 4: Run full suite one final time**

Run: `pytest -v && python validate.py`
Expected: All tests pass, validation passes

**Step 5: Commit**

```bash
git add CLAUDE.md MANIFEST.md .github/workflows/validate.yml
git commit -m "docs: update CLAUDE.md and MANIFEST.md with test commands, add tests to CI"
```
