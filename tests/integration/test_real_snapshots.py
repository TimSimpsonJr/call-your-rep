"""Integration smoke tests using real saved HTML from live sites."""

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
    return [s["file"].replace(".html", "") for s in _load_manifest()]


def _load_snapshots():
    return _load_manifest()


@pytest.mark.integration
@pytest.mark.parametrize("snapshot", _load_snapshots(), ids=_snapshot_ids())
def test_snapshot_parse(snapshot):
    filepath = os.path.join(SNAPSHOTS_DIR, snapshot["file"])
    if not os.path.exists(filepath):
        pytest.skip(f"Snapshot file not found: {snapshot['file']}")

    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    module = importlib.import_module(snapshot["adapter_module"])
    adapter_class = getattr(module, snapshot["adapter_class"])

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

    min_members = snapshot.get("min_members", 1)
    assert len(members) >= min_members, (
        f"Expected at least {min_members} members, got {len(members)}"
    )

    for i, member in enumerate(members):
        assert member.get("name"), f"Member {i} has no name"
        assert isinstance(member.get("title", ""), str)
