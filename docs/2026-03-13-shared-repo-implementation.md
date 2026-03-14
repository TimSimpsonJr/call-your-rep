# Call Your Rep: Shared Repo Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract scraper infrastructure and legislator data from deflocksc-website into a standalone `open-civics` repo, publish as two npm packages, and update deflocksc-website to consume them.

**Architecture:** Monorepo with Python scrapers producing JSON data, published as `open-civics` (rep contact data) and `open-civics-boundaries` (district GeoJSON) on npm. Scrapers commit to a `data-update` branch, validation auto-merges to `main`, weekly npm publish.

**Tech Stack:** Python 3.12 (scrapers), npm (publishing), GitHub Actions (CI/CD), Astro/Vite (consumer)

**Design doc:** `docs/plans/2026-03-13-shared-repo-design.md`

---

## Phase 1: Create the new repo and scaffold structure

### Task 1: Create GitHub repo and initialize

**Step 1: Create the repo on GitHub**

Run:
```bash
gh repo create TimSimpsonJr/open-civics --public --description "US legislator contact data — scraped, validated, and published as npm packages" --clone
```

**Step 2: Navigate to the new repo**

Run:
```bash
cd open-civics
```

**Step 3: Create directory structure**

Run:
```bash
mkdir -p scrapers/adapters data/sc/local data/sc/boundaries .github/workflows
```

**Step 4: Create initial files**

Create `README.md`:
```markdown
# open-civics

US legislator contact data — scraped, validated, and published as npm packages.

## Packages

- **`open-civics`** — Representative contact info (name, email, phone, party, district)
- **`open-civics-boundaries`** — District boundary GeoJSON for client-side matching

## Data structure

```
data/
└── sc/
    ├── state.json          # SC state legislators (senate + house)
    ├── local/
    │   ├── county-greenville.json
    │   ├── place-greenville.json
    │   └── ...
    └── boundaries/
        ├── sldu.json       # Senate districts
        ├── sldl.json       # House districts
        └── ...
```

## Usage

```bash
npm install open-civics
```

```js
import scState from 'open-civics/sc/state.json';
import greenvilleCounty from 'open-civics/sc/local/county-greenville.json';
```

For boundary data:

```bash
npm install open-civics-boundaries
```

```js
import senateBoundaries from 'open-civics-boundaries/sc/sldu.json';
```

## Scraping

Requires Python 3.12+.

```bash
pip install -r requirements.txt
python -m scrapers --state SC          # all SC data
python -m scrapers --state SC --state-only   # state legislators only
python -m scrapers --state SC --local-only   # local councils only
python -m scrapers --dry-run           # preview without scraping
```

## Adding a new state

1. Add state block to `registry.json`
2. Add email convention to `scrapers/state_email_rules.py`
3. Run `python -m scrapers --state XX`
4. Add local adapters as needed
```

Create `requirements.txt`:
```
requests
beautifulsoup4
geopandas
shapely
```

Create `.gitignore`:
```
__pycache__/
*.pyc
.env
node_modules/
*.egg-info/
dist/
.DS_Store
```

**Step 5: Commit scaffold**

Run:
```bash
git add -A && git commit -m "chore: scaffold repo structure"
```

---

### Task 2: Create package.json files

**Step 1: Create main package.json for `open-civics`**

Create `package.json`:
```json
{
  "name": "open-civics",
  "version": "0.1.0",
  "description": "US legislator contact data — names, emails, phones, districts",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/TimSimpsonJr/open-civics"
  },
  "files": [
    "data/**/state.json",
    "data/**/local/"
  ],
  "exports": {
    "./*": "./data/*"
  },
  "keywords": [
    "legislators",
    "representatives",
    "congress",
    "contact",
    "civic",
    "government"
  ]
}
```

**Step 2: Create boundaries package.json**

Create `boundaries-package.json`:
```json
{
  "name": "open-civics-boundaries",
  "version": "0.1.0",
  "description": "US legislative district boundary GeoJSON for client-side matching",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/TimSimpsonJr/open-civics"
  },
  "files": [
    "data/**/boundaries/"
  ],
  "exports": {
    "./*": "./data/*"
  },
  "keywords": [
    "districts",
    "boundaries",
    "geojson",
    "legislators",
    "civic"
  ]
}
```

**Step 3: Commit**

Run:
```bash
git add package.json boundaries-package.json && git commit -m "chore: add npm package.json files"
```

---

## Phase 2: Extract scrapers from deflocksc-website

### Task 3: Copy and adapt the scraper package

The source files are in `deflocksc-website/scripts/scrape_reps/`. Copy them to `scrapers/` in the new repo, updating paths and imports.

**Step 1: Copy adapter files verbatim**

Copy these files from `deflocksc-website/scripts/scrape_reps/adapters/` to `scrapers/adapters/`:
- `base.py` — no changes needed
- `civicplus.py` — no changes needed (relative import `from .base import BaseAdapter` still works)
- `greenville_county.py` — no changes needed
- `greenville_city.py` — no changes needed

Copy `scrapers/adapters/__init__.py` (empty file).

**Step 2: Copy and adapt state.py**

Copy `deflocksc-website/scripts/scrape_reps/state.py` to `scrapers/state.py`.

Changes needed:
- Update User-Agent string from `DeflockSC-RepScraper` to `OpenCivics-Scraper/1.0 (+https://github.com/TimSimpsonJr/open-civics)`
- The `update_state_legislators` function writes directly to a path — this is fine, the CLI will pass the new path

**Step 3: Create state_email_rules.py**

Create `scrapers/state_email_rules.py`:
```python
"""Per-state email conventions for backfilling missing emails from OpenStates.

When OpenStates data is missing an email address, the scraper can generate one
using the state's known email format. Generated emails are flagged with
"emailVerified": false so consumers know they're unverified.

To add a new state: add an entry to STATE_EMAIL_RULES with the chamber-specific
domain and format string. Format placeholders:
    {first}  - lowercase first name
    {last}   - lowercase last name
    {first1} - first letter of first name (lowercase)
"""

STATE_EMAIL_RULES = {
    "SC": {
        "senate": {"domain": "scsenate.gov", "format": "{first}{last}"},
        "house": {"domain": "schouse.gov", "format": "{first}{last}"},
    },
    # Add states as needed:
    # "NC": {
    #     "senate": {"domain": "ncleg.gov", "format": "{first}.{last}"},
    #     "house": {"domain": "ncleg.gov", "format": "{first}.{last}"},
    # },
}


def generate_email(state: str, chamber: str, first_name: str, last_name: str) -> str | None:
    """Generate an email address from state email rules.

    Returns the generated email or None if no rule exists for the state/chamber.
    """
    rules = STATE_EMAIL_RULES.get(state, {})
    chamber_rule = rules.get(chamber)
    if not chamber_rule:
        return None

    domain = chamber_rule["domain"]
    fmt = chamber_rule["format"]

    email = fmt.format(
        first=first_name.lower().replace(" ", ""),
        last=last_name.lower().replace(" ", ""),
        first1=first_name[0].lower() if first_name else "",
    )

    return f"{email}@{domain}"
```

**Step 4: Copy and adapt boundaries.py**

Copy `deflocksc-website/scripts/build-districts.py` to `scrapers/boundaries.py`.

Changes needed:
- Update path constants: `OUTPUT_DIR` and `REGISTRY_PATH` to use the new repo layout
  - `OUTPUT_DIR` = `os.path.join(PROJECT_ROOT, "data")` (will need state subdir passed in)
  - `REGISTRY_PATH` = `os.path.join(PROJECT_ROOT, "registry.json")`
- Update User-Agent string
- Update `collect_boundary_entries()` to read from the new registry format (`states.SC.stateBoundaries` and `states.SC.jurisdictions[].boundary`)
- Output paths should be under `data/<state>/boundaries/` instead of `public/districts/`

**Step 5: Create scrapers/__init__.py**

Create `scrapers/__init__.py` (empty file).

**Step 6: Create the new CLI entry point**

Create `scrapers/__main__.py`:
```python
"""
Scrape representative data for US jurisdictions.

Reads registry.json, dispatches adapters, updates data files.

Usage:
    python -m scrapers                           # scrape all
    python -m scrapers --state SC                # one state
    python -m scrapers --state SC --state-only   # state legislators only
    python -m scrapers --state SC --local-only   # local councils only
    python -m scrapers --state SC --boundaries-only
    python -m scrapers --jurisdiction county:greenville
    python -m scrapers --dry-run
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.join(SCRIPT_DIR, "..")
REGISTRY_PATH = os.path.join(PROJECT_ROOT, "registry.json")

from .adapters.civicplus import CivicPlusAdapter
from .adapters.greenville_city import GreenvilleCityAdapter
from .adapters.greenville_county import GreenvilleCountyAdapter

ADAPTERS = {
    "civicplus": CivicPlusAdapter,
    "greenville_city": GreenvilleCityAdapter,
    "greenville_county": GreenvilleCountyAdapter,
}


def load_registry() -> dict:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def get_adapter(entry: dict):
    """Return an adapter instance for a registry entry, or None for manual."""
    adapter_name = entry.get("adapter", "manual")
    if adapter_name == "manual":
        return None
    cls = ADAPTERS.get(adapter_name)
    if cls is None:
        print(f"  WARNING: No adapter registered for '{adapter_name}', skipping {entry['id']}")
        return None
    return cls(entry)


def scrape_state(state_code: str, state_config: dict, dry_run: bool = False):
    """Download OpenStates CSV and update state.json."""
    source_url = state_config.get("openStatesUrl", "")
    output_path = os.path.join(PROJECT_ROOT, "data", state_code.lower(), "state.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    print(f"\n=== {state_code} State Legislators ===")
    print(f"  Source: {source_url}")

    if dry_run:
        print(f"  [DRY RUN] Would download and update {output_path}")
        return

    from .state import update_state_legislators
    update_state_legislators(source_url, output_path)


def scrape_local(state_code: str, state_config: dict, jurisdiction_filter: str = None, dry_run: bool = False):
    """Run adapters for local jurisdictions and update per-jurisdiction JSON files."""
    local_dir = os.path.join(PROJECT_ROOT, "data", state_code.lower(), "local")
    os.makedirs(local_dir, exist_ok=True)

    for entry in state_config.get("jurisdictions", []):
        jid = entry["id"]

        if jurisdiction_filter and jid != jurisdiction_filter:
            continue

        print(f"\n--- {entry['name']} ({jid}) ---")

        adapter = get_adapter(entry)
        if adapter is None:
            print(f"  Skipping (manual adapter)")
            continue

        # Output filename: county:greenville -> county-greenville.json
        filename = jid.replace(":", "-") + ".json"
        output_path = os.path.join(local_dir, filename)

        if dry_run:
            print(f"  [DRY RUN] Would scrape {entry.get('url', '?')} -> {output_path}")
            continue

        try:
            members = adapter.scrape()
            print(f"  Scraped {len(members)} members")

            data = {
                "meta": {
                    "state": state_code,
                    "level": "local",
                    "jurisdiction": jid,
                    "label": entry["name"],
                    "lastUpdated": __import__("datetime").date.today().isoformat(),
                    "adapter": entry.get("adapter", "manual"),
                },
                "members": members,
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")

            print(f"  Wrote {output_path}")
        except Exception as e:
            print(f"  ERROR: {e}")


def scrape_boundaries(state_code: str, state_config: dict, dry_run: bool = False):
    """Build district boundary GeoJSON files."""
    from .boundaries import build_all_boundaries
    output_dir = os.path.join(PROJECT_ROOT, "data", state_code.lower(), "boundaries")
    os.makedirs(output_dir, exist_ok=True)
    build_all_boundaries(state_config, output_dir, dry_run=dry_run)


def main():
    parser = argparse.ArgumentParser(description="Scrape US representative data.")
    parser.add_argument("--state", type=str, help="Scrape a single state by code (e.g., SC)")
    parser.add_argument("--state-only", action="store_true", help="Only update state legislators")
    parser.add_argument("--local-only", action="store_true", help="Only update local councils")
    parser.add_argument("--boundaries-only", action="store_true", help="Only update boundaries")
    parser.add_argument("--jurisdiction", type=str, help="Scrape a single jurisdiction by ID")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without scraping")
    args = parser.parse_args()

    registry = load_registry()
    states = registry.get("states", {})

    if args.state:
        target_states = {args.state.upper(): states.get(args.state.upper())}
        if target_states[args.state.upper()] is None:
            print(f"ERROR: State '{args.state}' not found in registry.json")
            sys.exit(1)
    else:
        target_states = states

    for state_code, state_config in target_states.items():
        print(f"\n{'='*60}")
        print(f"  {state_code}")
        print(f"{'='*60}")

        run_all = not (args.state_only or args.local_only or args.boundaries_only)

        if run_all or args.state_only:
            scrape_state(state_code, state_config, dry_run=args.dry_run)

        if run_all or args.local_only:
            scrape_local(state_code, state_config, jurisdiction_filter=args.jurisdiction, dry_run=args.dry_run)

        if run_all or args.boundaries_only:
            scrape_boundaries(state_code, state_config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
```

**Step 7: Commit scrapers**

Run:
```bash
git add scrapers/ && git commit -m "feat: add scraper package (extracted from deflocksc-website)"
```

---

### Task 4: Create the registry.json

Restructure the current flat registry into the state-nested format.

**Step 1: Create registry.json**

Create `registry.json` with SC data restructured from the current `deflocksc-website/src/data/registry.json`. The key change is nesting everything under `states.SC`:

```json
{
  "states": {
    "SC": {
      "openStatesUrl": "https://data.openstates.org/people/current/sc.csv",
      "emailRules": "sc",
      "stateBoundaries": [
        {
          "id": "sldu",
          "name": "SC Senate Districts",
          "source": "tiger",
          "url": "https://www2.census.gov/geo/tiger/TIGER2024/SLDU/tl_2024_45_sldu.zip",
          "districtField": "SLDUST",
          "file": "sldu.json"
        },
        {
          "id": "sldl",
          "name": "SC House Districts",
          "source": "tiger",
          "url": "https://www2.census.gov/geo/tiger/TIGER2024/SLDL/tl_2024_45_sldl.zip",
          "districtField": "SLDLST",
          "file": "sldl.json"
        }
      ],
      "jurisdictions": [
        ... (copy all jurisdictions from current registry.json, adapting field names)
      ]
    }
  }
}
```

The jurisdiction entries keep the same data but with slightly flattened boundary fields:
- `boundarySource` -> `boundary.source`
- `boundaryUrl` -> `boundary.url`
- `boundaryDistrictField` -> `boundary.districtField`
- `boundaryFile` -> `boundary.file`
- `boundaryConfig` -> `boundary.config`

**Step 2: Commit**

Run:
```bash
git add registry.json && git commit -m "feat: add registry.json with SC jurisdictions"
```

---

### Task 5: Copy data files

**Step 1: Copy state legislator data**

Copy `deflocksc-website/src/data/state-legislators.json` to `data/sc/state.json`.

Wrap the existing data (which has just `senate` and `house` keys) in a `meta` block:

```json
{
  "meta": {
    "state": "SC",
    "level": "state",
    "lastUpdated": "2026-03-13",
    "source": "openstates"
  },
  "senate": { ... },
  "house": { ... }
}
```

**Step 2: Split local councils into per-jurisdiction files**

The current `deflocksc-website/src/data/local-councils.json` is one big object keyed by jurisdiction ID. Split it into individual files under `data/sc/local/`:

For each key (e.g., `county:greenville`), create `data/sc/local/county-greenville.json`:
```json
{
  "meta": {
    "state": "SC",
    "level": "local",
    "jurisdiction": "county:greenville",
    "label": "Greenville County Council",
    "lastUpdated": "2026-03-13",
    "adapter": "greenville_county"
  },
  "members": [ ... ]
}
```

Write a quick Python script to do the split:
```python
import json, os

with open("local-councils.json") as f:
    data = json.load(f)

os.makedirs("data/sc/local", exist_ok=True)

for jid, council in data.items():
    filename = jid.replace(":", "-") + ".json"
    out = {
        "meta": {
            "state": "SC",
            "level": "local",
            "jurisdiction": jid,
            "label": council.get("label", ""),
            "lastUpdated": "2026-03-13",
            "adapter": "unknown",
        },
        "members": council.get("members", []),
    }
    with open(f"data/sc/local/{filename}", "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {filename}")
```

**Step 3: Copy boundary files**

Copy all files from `deflocksc-website/public/districts/` to `data/sc/boundaries/`.

**Step 4: Commit**

Run:
```bash
git add data/ && git commit -m "feat: add SC data (state legislators, local councils, boundaries)"
```

---

### Task 6: Create and adapt validate.py

**Step 1: Copy and adapt validation**

Copy `deflocksc-website/scripts/validate-data.py` to `validate.py`.

Changes needed:
- Update `DATA_DIR` to point to `data/` (not `src/data/`)
- Update `DISTRICTS_DIR` to scan `data/*/boundaries/` directories
- Update `validate_state_legislators` to expect the new schema (with `meta` block)
- Update `validate_local_councils` to validate per-file format (with `meta` block) instead of the monolithic format
- Remove `validate_bills` and `validate_action_letters` (those stay in deflocksc-website)
- Update `validate_registry` to match the new nested registry format
- Add sanity check: compare member counts against previous data to catch >50% drops
- Walk `data/*/` directories to discover which states to validate

**Step 2: Commit**

Run:
```bash
git add validate.py && git commit -m "feat: add data validation script"
```

---

## Phase 3: GitHub Actions

### Task 7: Create scrape workflow

**Step 1: Create `.github/workflows/scrape.yml`**

```yaml
name: Scrape Rep Data

on:
  schedule:
    # Weekly Monday 10am ET (15:00 UTC)
    - cron: '0 15 * * 1'
    # Monthly 1st at 10am ET
    - cron: '0 15 1 * *'
  workflow_dispatch:
    inputs:
      state:
        description: 'State code (blank = all)'
        required: false
        default: ''
      scope:
        description: 'Which data to scrape'
        required: true
        default: 'all'
        type: choice
        options:
          - all
          - state-only
          - local-only
          - boundaries-only

jobs:
  scrape:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt

      - name: Run scrapers
        run: |
          ARGS=""
          if [ -n "${{ github.event.inputs.state }}" ]; then
            ARGS="$ARGS --state ${{ github.event.inputs.state }}"
          fi
          SCOPE="${{ github.event.inputs.scope || 'all' }}"
          if [ "$SCOPE" = "state-only" ]; then
            ARGS="$ARGS --state-only"
          elif [ "$SCOPE" = "local-only" ]; then
            ARGS="$ARGS --local-only"
          elif [ "$SCOPE" = "boundaries-only" ]; then
            ARGS="$ARGS --boundaries-only"
          fi
          python -m scrapers $ARGS

      - name: Validate data
        run: python validate.py

      - name: Create PR if data changed
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          if git diff --quiet data/; then
            echo "No data changes detected"
            exit 0
          fi

          BRANCH="data-update/$(date +%Y-%m-%d-%H%M)"
          git checkout -b "$BRANCH"
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/
          git commit -m "chore: update rep data $(date +%Y-%m-%d)"
          git push -u origin "$BRANCH"
          gh pr create \
            --title "chore: update rep data $(date +%Y-%m-%d)" \
            --body "Automated data update from scraper run. Validation passed." \
            --base main
```

**Step 2: Create `.github/workflows/validate.yml`**

```yaml
name: Validate Data

on:
  pull_request:
    paths:
      - 'data/**'
      - 'registry.json'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: python validate.py

  auto-merge:
    needs: validate
    runs-on: ubuntu-latest
    if: startsWith(github.head_ref, 'data-update/')
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - name: Auto-merge data update PR
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh pr merge ${{ github.event.pull_request.number }} \
            --squash \
            --auto \
            --delete-branch
```

**Step 3: Create `.github/workflows/publish.yml`**

```yaml
name: Publish npm Packages

on:
  schedule:
    # Weekly Friday 6pm ET (23:00 UTC)
    - cron: '0 23 * * 5'
  workflow_dispatch:

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://registry.npmjs.org'

      - name: Check if data changed since last tag
        id: check
        run: |
          LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
          if [ -z "$LAST_TAG" ]; then
            echo "changed=true" >> $GITHUB_OUTPUT
          elif git diff --quiet "$LAST_TAG" -- data/; then
            echo "changed=false" >> $GITHUB_OUTPUT
          else
            echo "changed=true" >> $GITHUB_OUTPUT
          fi

      - name: Bump version and publish open-civics
        if: steps.check.outputs.changed == 'true'
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
        run: |
          npm version patch --no-git-tag-version
          npm publish --access public

      - name: Publish open-civics-boundaries
        if: steps.check.outputs.changed == 'true'
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
        run: |
          cp boundaries-package.json package.json
          npm version patch --no-git-tag-version
          npm publish --access public

      - name: Tag release
        if: steps.check.outputs.changed == 'true'
        run: |
          VERSION=$(node -p "require('./package.json').version")
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git tag "v$VERSION"
          git push --tags
```

**Step 4: Commit workflows**

Run:
```bash
git add .github/ && git commit -m "ci: add scrape, validate, and publish workflows"
```

---

### Task 8: Add CLAUDE.md and MANIFEST.md

**Step 1: Create CLAUDE.md**

Create `CLAUDE.md` with project-specific instructions for Claude:
- Python 3.12, run scrapers with `python -m scrapers`
- Validate with `python validate.py`
- Registry format is nested by state
- Adapter pattern: extend `BaseAdapter` in `scrapers/adapters/`
- Two npm packages from one repo
- Data safety gate: scrapers never commit to main directly

**Step 2: Generate MANIFEST.md**

Follow the global CLAUDE.md manifest format: Stack, Structure, Key Relationships.

**Step 3: Commit**

Run:
```bash
git add CLAUDE.md MANIFEST.md && git commit -m "docs: add CLAUDE.md and MANIFEST.md"
```

---

### Task 9: Move local-adapter-audit.md to new repo

**Step 1: Copy the file**

Copy `deflocksc-website/docs/local-adapter-audit.md` to `docs/local-adapter-audit.md` in the new repo.

**Step 2: Commit**

Run:
```bash
mkdir -p docs && git add docs/local-adapter-audit.md && git commit -m "docs: add local adapter audit from deflocksc-website"
```

---

### Task 10: Push and verify

**Step 1: Push to GitHub**

Run:
```bash
git push -u origin main
```

**Step 2: Verify repo structure on GitHub**

Run:
```bash
gh repo view TimSimpsonJr/open-civics --web
```

**Step 3: Test scraper locally**

Run:
```bash
python -m scrapers --state SC --dry-run
```
Expected: prints all SC sources without actually fetching.

**Step 4: Test validation locally**

Run:
```bash
python validate.py
```
Expected: all checks pass.

---

## Phase 4: Update deflocksc-website to consume packages

> **Note:** This phase happens AFTER the npm packages are published (or can be done with local linking for dev). It can be done in a separate session.

### Task 11: Install packages in deflocksc-website

**Step 1: Install open-civics**

Run (from deflocksc-website):
```bash
npm install open-civics open-civics-boundaries
```

**Step 2: Update imports in ActionModal.astro**

Change:
```typescript
import stateLegislators from '../data/state-legislators.json';
import localCouncils from '../data/local-councils.json';
import registryFull from '../data/registry.json';
```

To:
```typescript
import stateLegislators from 'open-civics/sc/state.json';
// Local councils need to be loaded differently since they're now split files
// Import them individually or use a glob import
```

This will require some refactoring of how local council data is loaded in ActionModal.astro, since it was previously one big object and is now split files. The specifics depend on how the modal uses the data.

**Step 3: Update district-matcher.ts boundary paths**

The boundary files will still be served from `/districts/` at runtime. Options:
- Copy boundary files from `node_modules/open-civics-boundaries/data/sc/boundaries/` to `public/districts/` at build time
- Or update the fetch paths in district-matcher.ts

A build-time copy script in `package.json` is cleanest:
```json
{
  "scripts": {
    "prebuild": "cp -r node_modules/open-civics-boundaries/data/sc/boundaries/* public/districts/"
  }
}
```

**Step 4: Remove extracted files**

Delete from deflocksc-website:
- `scripts/scrape_reps/` (entire directory)
- `scripts/build-districts.py`
- `scripts/validate-data.py`
- `src/data/state-legislators.json`
- `src/data/local-councils.json`
- `src/data/registry.json`
- `.github/workflows/scrape-reps.yml`

Keep:
- `src/data/bills.json` (separate concern)
- `src/data/action-letters.json` (site-specific)
- `src/data/foia-contacts.json` (site-specific)
- `src/data/toolkit-*.json` (site-specific)
- `.github/workflows/scrape-bills.yml` (separate concern)
- `public/districts/` (still needed for runtime serving; populated from package at build time)

**Step 5: Test the site builds and works**

Run:
```bash
npm run build
```

Verify: site builds without errors, action modal loads rep data correctly.

**Step 6: Commit**

Run:
```bash
git add -A && git commit -m "refactor: consume rep data from open-civics npm packages"
```
