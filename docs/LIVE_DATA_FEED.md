# Live disaster feed integration

## Global multi-hazard source

ResQ-AI includes a read-only adapter for the official [Global Disaster Awareness and Coordination System (GDACS)](https://www.gdacs.org/Alerts/).

- **API documentation:** https://www.gdacs.org/gdacsapi/swagger/index.html
- **Event endpoint:** https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH
- **Coverage:** earthquakes, tropical cyclones, floods, volcanoes, forest fires, and droughts. Tsunami-related information may be associated with earthquake events.
- **Window:** selectable recent 7, 30, or 90 days.
- **Traceability:** event type, name, country/area, alert level, available timestamps, source link, and retrieval timestamp.
- **Refresh:** successful snapshots are cached for five minutes.
- **Failure behavior:** the page displays an explicit unavailable state; it never substitutes sample events.

GDACS is a global disaster-awareness and coordination system supported by the United Nations and European Commission. See its official feed reference and API documentation for coverage, field definitions, and terms of use.

## USGS earthquakes

The command center's existing read-only feed uses the public [USGS GeoJSON — all earthquakes in the past day](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson). It reports magnitude, location, UTC event time, depth, tsunami flag, source-generated timestamp, and USGS event links.

## India government warnings

The separate Live Government Alerts page can connect to IMD district nowcasts/warnings and an authorized NDMA SACHET/CAP feed. Those connectors require valid IMD API access and an authorized SACHET feed URL. See [LIVE_GOVERNMENT_DATA.md](LIVE_GOVERNMENT_DATA.md).

## Important separation

Global hazard events and official weather warnings are source-reported observations. They are not automatically converted into verified local rescue incidents, assigned an operational priority score, or used to recommend dispatch. A global event feed cannot tell ResQ-AI which ambulances are currently available, which shelters have open capacity, or which roads are passable. Those operational records must come from authorized live systems or direct updates by responsible operators.

**Important current limitation:** the command center's incident, resource, hospital, shelter, and road CSVs are still simulated prototype data. Do not treat them as current real-world status. The GDACS/USGS feeds are informational and are not emergency alert or dispatch services.
