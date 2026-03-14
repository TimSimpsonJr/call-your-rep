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
