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
