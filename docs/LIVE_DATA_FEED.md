# Live disaster feed integration

## Current integration

The command center includes a read-only live feed from the U.S. Geological Survey (USGS) Earthquake Hazards Program.

- **Feed:** [USGS GeoJSON — all earthquakes in the past day](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson)
- **Source metadata:** USGS feed generation timestamp
- **Fetch timestamp:** time the application successfully retrieved the feed, displayed in UTC
- **Refresh behavior:** successful responses are cached for up to five minutes
- **Data shown:** magnitude, location, UTC event time, depth, tsunami flag, and link to the USGS event page
- **Failure behavior:** shows an explicit unavailable state; does not invent events or silently present old data as fresh

## Important separation

USGS earthquake events are displayed as a separate live intelligence feed. They are **not** automatically inserted into the simulated incident queue, assigned a priority score, or used to recommend dispatch. This avoids mixing public global earthquake observations with the prototype's simulated Pune-area operational data.

The application currently uses live USGS earthquake data only; floods, wildfires, storms, and other hazards are not covered by this feed. The live feed is informational and is not an emergency alert service.

## Verification

Run:

```bash
pytest -q
```
