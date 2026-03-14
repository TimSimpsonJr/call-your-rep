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
    state.json                # State legislators (senate + house) by district
    local/
      county-greenville.json  # County council reps by jurisdiction
      place-greenville.json   # City council reps by jurisdiction
      ...
    boundaries/
      sldu.json               # State senate district boundaries
      sldl.json               # State house district boundaries
      county-greenville.json  # County council district boundaries
      place-greenville.json   # City council district boundaries
      ...
```

## Usage

```js
// Rep contact data
import scState from 'call-your-rep/sc/state.json';
import greenvilleCounty from 'call-your-rep/sc/local/county-greenville.json';
import greenvilleCity from 'call-your-rep/sc/local/place-greenville.json';

// District boundaries
import senateBoundaries from 'call-your-rep-boundaries/sc/boundaries/sldu.json';
import houseBoundaries from 'call-your-rep-boundaries/sc/boundaries/sldl.json';
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
