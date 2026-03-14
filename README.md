# open-civics

Structured contact data for US elected officials — state legislators, county councils, and city councils — scraped weekly and published as npm packages.

South Carolina is fully covered: 170 state legislators and 96 local jurisdictions (every county and incorporated municipality).

## Packages

Install via npm:

```bash
npm install open-civics            # contact data
npm install open-civics-boundaries # district boundary GeoJSON
```

| Package | What's in it |
|---------|-------------|
| `open-civics` | Names, titles, emails, phones, districts for state and local reps |
| `open-civics-boundaries` | GeoJSON district boundaries for client-side point-in-polygon matching |

## What the data looks like

Each local jurisdiction file has a `meta` block and a `members` array:

```json
{
  "meta": {
    "state": "SC",
    "level": "local",
    "jurisdiction": "county:greenville",
    "label": "Greenville County Council",
    "lastUpdated": "2026-03-14"
  },
  "members": [
    {
      "name": "Benton Blount",
      "title": "Chairman, District 19",
      "email": "BBlount@greenvillecounty.org",
      "phone": "(864) 483-2474"
    }
  ]
}
```

State legislator files are keyed by district number with senate/house chambers:

```json
{
  "meta": { "state": "SC", "level": "state" },
  "senate": {
    "1": { "name": "...", "district": "1", "party": "R", "email": "...", "phone": "..." }
  },
  "house": {
    "1": { "name": "...", "district": "1", "party": "D", "email": "...", "phone": "..." }
  }
}
```

## Usage

```js
// State legislators
import scState from 'open-civics/sc/state.json';
const senator = scState.senate["1"];

// Local councils
import greenvilleCounty from 'open-civics/sc/local/county-greenville.json';
const members = greenvilleCounty.members;

// District boundaries (GeoJSON FeatureCollection)
import senateBoundaries from 'open-civics-boundaries/sc/boundaries/sldu.json';
import houseBoundaries from 'open-civics-boundaries/sc/boundaries/sldl.json';
import countyBoundaries from 'open-civics-boundaries/sc/boundaries/county-greenville.json';
```

Boundary files are standard GeoJSON FeatureCollections. Each feature has a `properties.district` field matching the district keys in the contact data. Use any point-in-polygon library (Turf.js, Mapbox, etc.) to find which district a user's address falls in.

## Data structure

```
data/
  sc/
    state.json                # State legislators (senate + house + governor)
    local/
      county-greenville.json  # Greenville County Council
      place-greenville.json   # Greenville City Council
      ...                     # 96 jurisdiction files total
    boundaries/
      sldu.json               # State senate district boundaries
      sldl.json               # State house district boundaries
      county-greenville.json  # County council district boundaries
      place-greenville.json   # City council district boundaries (where available)
      ...
```

## How scraping works

Data is scraped from government websites using Python adapters — one per site pattern. Five shared adapters handle the most common CMS platforms:

| Adapter | Sites | How it works |
|---------|-------|-------------|
| Revize | ~30 cities | Parses bold name / mailto / phone patterns |
| CivicPlus | ~14 counties | Parses staff directory tables with JS-obfuscated emails |
| TableAdapter | ~10 jurisdictions | Auto-detects HTML tables with name/email/phone columns |
| GenericMailto | ~15 cities | Finds mailto links in WordPress/Drupal content areas |
| DrupalViews | ~3 counties | Parses Drupal views-row and person-item patterns |

The remaining jurisdictions use bespoke adapters, MASC (Municipal Association of SC), or SCAC (SC Association of Counties) as data sources.

Boundary data comes from the US Census TIGER/Line shapefiles (state districts) and ArcGIS REST services (local districts).

## Running the scrapers

Requires Python 3.12+.

```bash
pip install -r requirements.txt

# Scrape everything for a state
python -m scrapers --state SC

# Scrape only state legislators
python -m scrapers --state SC --state-only

# Scrape only local councils
python -m scrapers --state SC --local-only

# Scrape state + local, skip boundaries (faster)
python -m scrapers --state SC --skip-boundaries

# Preview what would run without scraping
python -m scrapers --dry-run

# Validate all data files
python validate.py
```

## Automation

Three GitHub Actions workflows keep data fresh:

- **Weekly scrape** (Mondays 10am ET): Runs state + local scrapers, opens a PR with changes
- **Monthly scrape** (1st of month 10am ET): Full scrape including boundary rebuilds
- **Validation**: Runs on every PR touching `data/` — auto-merges `data-update/*` branches if validation passes
- **Publish**: Weekly npm publish if data changed since last release

## Running tests

```bash
pip install -r requirements-dev.txt

# Unit tests (fast, no network)
pytest tests/unit/ -v

# All tests including integration
pytest -v

# Refresh integration test snapshots from live sites
python scripts/refresh_snapshots.py
```

## Adding a new state

1. Add a state block to `registry.json` under `states.XX`
2. Add email format rules to `scrapers/state_email_rules.py`
3. Run `python -m scrapers --state XX --state-only` to pull legislators
4. Add local jurisdiction adapters as needed (see `CLAUDE.md` for the adapter selection checklist)
5. Add boundary sources to `registry.json` and run `python -m scrapers --state XX --boundaries-only`

## License

See [LICENSE](LICENSE) for details.
