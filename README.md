# call-your-rep

US legislator contact data — scraped, validated, and published as npm packages.

## Packages

| Package | Description |
|---------|-------------|
| `call-your-rep` | Rep contact data: names, emails, phones, districts |
| `call-your-rep-boundaries` | District boundary GeoJSON for client-side matching |

## Data structure

```
data/
  sc/
    state.json          # State-level reps (governor, senators, etc.)
    local/
      greenville.json   # City/county reps by jurisdiction
      charleston.json
      ...
    boundaries/
      senate.geojson    # State senate district boundaries
      house.geojson     # State house district boundaries
      ...
```

## Usage

```js
// Rep contact data
import scState from 'call-your-rep/sc/state.json';
import greenville from 'call-your-rep/sc/local/greenville.json';

// District boundaries
import senateBoundaries from 'call-your-rep-boundaries/sc/boundaries/senate.geojson';
```

## Scraping

Requires Python 3.12+.

```bash
pip install -r requirements.txt
python -m scrapers --state SC
```

This scrapes legislator data for the given state and writes JSON to `data/<state>/`.

## Adding a new state

1. Create an adapter in `scrapers/adapters/<state>.py`
2. The adapter should export a `scrape()` function that returns structured rep data
3. Run the scraper to populate `data/<state>/`
4. Add boundary processing if the state needs client-side district matching
