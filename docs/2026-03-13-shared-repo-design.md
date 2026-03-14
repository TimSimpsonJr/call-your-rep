# Shared Legislator Data Repo: Design

## Goal

Extract scraper infrastructure and legislator data from deflocksc-website into a
standalone repo (`open-civics`) that serves as the single source of truth for
representative contact info. Start with SC, scaffold for all US states + federal.

## Approach

Monorepo containing Python scrapers and JSON data output, published as two npm
packages: `open-civics` (rep contact data) and `open-civics-boundaries`
(district GeoJSON). Consumers install via npm. Scrapers run on GitHub Actions
and auto-publish after validation.

## Repo Structure

```
open-civics/
├── scrapers/
│   ├── __init__.py
│   ├── __main__.py              # CLI: python -m scrapers [--state SC] [--local-only]
│   ├── state.py                 # OpenStates CSV download + email backfill
│   ├── state_email_rules.py     # Per-state email conventions
│   ├── boundaries.py            # Census TIGER + ArcGIS boundary builder
│   └── adapters/
│       ├── base.py
│       ├── civicplus.py
│       ├── greenville_county.py
│       ├── greenville_city.py
│       └── ...
├── data/
│   └── sc/
│       ├── state.json
│       ├── local/
│       │   ├── county-greenville.json
│       │   ├── place-greenville.json
│       │   └── ...
│       └── boundaries/
│           ├── sldu.json
│           ├── sldl.json
│           ├── county-greenville.json
│           └── ...
├── registry.json
├── validate.py
├── requirements.txt
├── package.json                 # open-civics (publishes data/ minus boundaries)
├── boundaries-package.json      # open-civics-boundaries (publishes boundaries)
├── .github/
│   └── workflows/
│       ├── scrape.yml           # Weekly state, monthly local+boundaries
│       ├── validate.yml         # PR check on data-update branches
│       └── publish.yml          # Weekly npm publish from main
├── CLAUDE.md
├── MANIFEST.md
└── README.md
```

## Data Schema

### State (`data/sc/state.json`)

```json
{
  "meta": {
    "state": "SC",
    "level": "state",
    "lastUpdated": "2026-03-13",
    "source": "openstates"
  },
  "senate": {
    "1": {
      "name": "Shane Massey",
      "district": "1",
      "party": "R",
      "email": "shanemassey@scsenate.gov",
      "phone": "(803) 212-6330",
      "photoUrl": "...",
      "website": "...",
      "source": "openstates",
      "lastUpdated": "2026-03-13"
    }
  },
  "house": { "...": "..." }
}
```

### Local (`data/sc/local/county-greenville.json`)

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
  "members": [
    {
      "name": "Joe Dill",
      "district": "17",
      "title": "Council Member",
      "email": "...",
      "phone": "...",
      "source": "scraped",
      "lastUpdated": "2026-03-13"
    }
  ]
}
```

### Email backfill

When OpenStates has no email, the scraper generates one from state-specific
rules and flags it:

```json
{
  "email": "janedoe@schouse.gov",
  "emailVerified": false
}
```

## Registry (`registry.json`)

Restructured by state so adding a state is self-contained:

```json
{
  "states": {
    "SC": {
      "openStatesUrl": "https://data.openstates.org/people/current/sc.csv",
      "emailRules": "sc",
      "stateBoundaries": [
        { "id": "sldu", "source": "tiger", "url": "...", "districtField": "SLDUST" },
        { "id": "sldl", "source": "tiger", "url": "...", "districtField": "SLDLST" }
      ],
      "jurisdictions": [
        {
          "id": "county:greenville",
          "name": "Greenville County Council",
          "adapter": "greenville_county",
          "url": "https://greenvillecounty.org/council",
          "districts": 12,
          "boundary": { "source": "arcgis", "url": "...", "districtField": "DISTRICT" }
        }
      ]
    }
  }
}
```

## CLI

```
python -m scrapers                           # scrape everything
python -m scrapers --state SC                # one state (state + local + boundaries)
python -m scrapers --state SC --state-only   # just state legislators
python -m scrapers --state SC --local-only   # just local councils
python -m scrapers --state SC --boundaries-only
python -m scrapers --jurisdiction county:greenville
python -m scrapers --dry-run
```

## npm Packages

### `open-civics`

```json
{
  "name": "open-civics",
  "version": "0.1.0",
  "files": ["data/"],
  "exports": {
    "./sc/*": "./data/sc/*"
  }
}
```

Consumer import: `import scState from 'open-civics/sc/state.json'`

### `open-civics-boundaries`

Separate package for district GeoJSON (large files). Same repo, separate
package.json. Consumer import: `import sldu from 'open-civics-boundaries/sc/sldu.json'`

## GitHub Actions

### `scrape.yml` — data collection

- Weekly: state legislators for all states in registry
- Monthly: local councils + boundaries
- Manual: workflow_dispatch with state/scope inputs
- Commits to `data-update` branch, opens PR to `main`

### `validate.yml` — PR check

- Runs on PRs touching `data/`
- Schema validation (required fields, types)
- Sanity checks: member count didn't drop >50%, no empty arrays where data existed
- If all checks pass, auto-merge to `main`
- If checks fail, PR stays open for manual review

### `publish.yml` — npm publish

- Runs weekly (Fridays) on `main`
- Only publishes if `data/` changed since last publish
- Bumps patch version, publishes both packages
- Requires `NPM_TOKEN` secret

## Migration from deflocksc-website

### Moves to open-civics

- `scripts/scrape_reps/` -> `scrapers/`
- `scripts/build-districts.py` -> `scrapers/boundaries.py`
- `src/data/state-legislators.json` -> `data/sc/state.json`
- `src/data/local-councils.json` -> split into `data/sc/local/*.json`
- `src/data/registry.json` -> `registry.json` (restructured by state)
- `scripts/validate-data.py` -> `validate.py`
- `.github/workflows/scrape-reps.yml` -> `.github/workflows/`
- `public/districts/*.json` -> `data/sc/boundaries/`

### Stays in deflocksc-website

- `src/scripts/action-modal/` (UI)
- `src/lib/district-matcher.ts` (geocoding + district lookup)
- All site content, styling, pages
- `docs/local-adapter-audit.md` (moves to new repo)

### Changes in deflocksc-website

- Add `open-civics` and `open-civics-boundaries` as npm dependencies
- Replace JSON imports to point at package paths
- Remove `scripts/scrape_reps/`, `scripts/build-districts.py`, `scripts/validate-data.py`
- Remove `src/data/state-legislators.json`, `src/data/local-councils.json`, `src/data/registry.json`
- Remove `public/districts/` boundary files
- Remove `.github/workflows/scrape-reps.yml`
- Add Dependabot rule to auto-update data packages

## Adding a New State

1. Add state block to `registry.json` (OpenStates URL, email rules, boundaries)
2. Add email convention to `state_email_rules.py`
3. Run `python -m scrapers --state NC`
4. Data appears at `data/nc/state.json`
5. Add local adapters as needed
6. Next publish cycle includes the new state

## v0.1 Scope

- Extract current SC scrapers + data
- Scaffold multi-state structure (directories, CLI flags, email rules config)
- Publish as `open-civics` + `open-civics-boundaries` on npm
- Update deflocksc-website to consume packages
- Safety gate: scraper -> PR -> validate -> auto-merge -> publish
- SC only; no other states populated yet
