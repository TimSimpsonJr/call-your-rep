# Migrating to open-civics

Instructions for replacing existing scraper infrastructure in DeflockSC and Call Y'all with the `open-civics` npm packages.

## What open-civics provides

Two npm packages, updated weekly via automated scrapers:

- **`open-civics`** — contact data (names, titles, emails, phones, districts, parties) for SC state legislators and 96 local jurisdictions
- **`open-civics-boundaries`** — GeoJSON district boundaries for client-side point-in-polygon matching

## Install

```bash
npm install open-civics open-civics-boundaries
```

## Data shapes

### State legislators (`open-civics/sc/state.json`)

```ts
{
  meta: { state: "SC", level: "state", lastUpdated: "2026-03-14" },
  senate: {
    [districtNumber: string]: {
      name: string,
      district: string,
      party: "R" | "D",
      email: string,
      phone: string,
      photoUrl?: string,
      website?: string
    }
  },
  house: { /* same shape */ },
  governor: { name, title, email, phone, website }
}
```

### Local councils (`open-civics/sc/local/county-greenville.json`)

```ts
{
  meta: {
    state: "SC",
    level: "local",
    jurisdiction: "county:greenville",  // or "place:greenville"
    label: "Greenville County Council",
    lastUpdated: "2026-03-14"
  },
  members: [
    {
      name: string,
      title: string,       // e.g. "Council Member, District 17"
      email?: string,
      phone?: string
    }
  ]
}
```

Jurisdiction naming: `county-{name}.json` for counties, `place-{name}.json` for cities/towns.

### Boundaries (`open-civics-boundaries/sc/boundaries/*.json`)

Standard GeoJSON FeatureCollections. Each feature has `properties.district` matching the district keys in contact data.

- `sldu.json` — state senate districts (46 features)
- `sldl.json` — state house districts (124 features)
- `county-{name}.json` — county council districts
- `place-{name}.json` — city council districts (where available)

## Import examples

```js
// State legislators
import scState from 'open-civics/sc/state.json';
const senator = scState.senate["1"];
const rep = scState.house["42"];
const governor = scState.governor;

// All senators as array
const allSenators = Object.values(scState.senate);

// Local councils
import greenvilleCounty from 'open-civics/sc/local/county-greenville.json';
const members = greenvilleCounty.members;

// Boundaries for point-in-polygon lookup
import senateBoundaries from 'open-civics-boundaries/sc/boundaries/sldu.json';
import houseBoundaries from 'open-civics-boundaries/sc/boundaries/sldl.json';
import countyBoundaries from 'open-civics-boundaries/sc/boundaries/county-greenville.json';
```

## Dynamic loading (if you need all jurisdictions)

```js
// Load all local council files dynamically
const localFiles = [
  'county-greenville', 'county-spartanburg', 'place-greenville',
  // ... full list at: https://github.com/TimSimpsonJr/open-civics/tree/master/data/sc/local
];

const councils = await Promise.all(
  localFiles.map(f => import(`open-civics/sc/local/${f}.json`))
);
```

## Point-in-polygon lookup (finding a user's reps by address)

Use any geocoding service to get lat/lng from an address, then use Turf.js (or similar) to find which districts contain that point:

```js
import * as turf from '@turf/turf';
import senateBoundaries from 'open-civics-boundaries/sc/boundaries/sldu.json';
import scState from 'open-civics/sc/state.json';

function findSenator(lat, lng) {
  const point = turf.point([lng, lat]);
  const district = senateBoundaries.features.find(f =>
    turf.booleanPointInPolygon(point, f)
  );
  if (!district) return null;
  return scState.senate[district.properties.district];
}
```

## Migration checklist

### 1. Remove existing scraper code
- Delete any scraper scripts, cron jobs, or serverless functions that fetch legislator data
- Delete any local JSON/DB storage of legislator contact info
- Delete any boundary/district data files you maintain

### 2. Replace data access
- Install packages: `npm install open-civics open-civics-boundaries`
- Replace all data reads with imports from the packages (see examples above)
- State legislators: `import scState from 'open-civics/sc/state.json'`
- Local councils: `import data from 'open-civics/sc/local/{jurisdiction}.json'`
- Boundaries: `import geo from 'open-civics-boundaries/sc/boundaries/{file}.json'`

### 3. Adapt to the data shape
- State data is keyed by district number, not an array — use `Object.values()` if you need arrays
- Local members are in a `members` array with `name`, `title`, `email`, `phone`
- Party info is only on state legislators (not local)
- Some local members may be missing email or phone (the `?` fields above)

### 4. Update any district lookup logic
- Replace any server-side geocoding/district lookup with client-side point-in-polygon using the boundary GeoJSON
- Or keep server-side if you prefer — just import the boundary files there instead

## Staying up to date

### Option A: Dependabot (recommended)

Add to `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    allow:
      - dependency-name: "open-civics"
      - dependency-name: "open-civics-boundaries"
```

This opens a PR whenever new data is published (weekly). Merge it to get fresh data.

### Option B: Pin to latest in CI

In your deploy/build pipeline:

```bash
npm update open-civics open-civics-boundaries
```

This pulls the latest version on every deploy.

### Option C: Use `*` or `>=` version range

In `package.json`:

```json
{
  "dependencies": {
    "open-civics": "*",
    "open-civics-boundaries": "*"
  }
}
```

Every `npm install` gets the latest. Less reproducible but always fresh.

### Recommended approach

Use Dependabot (Option A). It gives you visibility into what changed, lets you review before merging, and keeps your lockfile deterministic.

## Update cadence

- **Contact data**: scraped and published weekly (Mondays). State legislators change rarely; local councils change when elections happen or members resign.
- **Boundary data**: rebuilt monthly (1st of month). Boundaries only change after redistricting (every 10 years for state, occasionally for local).
- **npm publish**: every Friday if data changed since last release.

## Available jurisdictions

96 local jurisdictions are covered — every SC county and incorporated municipality. Full list of files:

https://github.com/TimSimpsonJr/open-civics/tree/master/data/sc/local

## Questions?

Source repo: https://github.com/TimSimpsonJr/open-civics
