"""Shared test fixtures for call-your-rep tests."""

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
