# Live Government Data

ResQ-AI includes a **Live Government Alerts** page that connects to official government feeds on demand. Live warnings are displayed separately from the operator-reported incident queue and never modify deterministic scores.

## Sources

### India Meteorological Department (IMD)

- Official API portal: https://api.imd.gov.in/public/index.php
- Official API reference: https://api.imd.gov.in/public/api_reference.html
- Data endpoints used: district nowcast and district warning under https://api.imd.gov.in/api/v1/
- Configure IMD_API_TOKEN using an issued credential from IMD. The app reports an unavailable source if the token or permission is missing.
- Optional IMD_API_BASE can select the API base documented by IMD. Do not point it to an untrusted host.

The adapter requests the documented districtnowcast and districtwarning resources, uses the configured authorization header, normalizes common response shapes, and caches successful JSON responses for five minutes. If IMD changes the API contract, update the adapter to match the current official reference.

### NDMA SACHET / India CAP

- Official portal: https://sachet.ndma.gov.in/
- Official CAP feed guide: https://sachet.ndma.gov.in/CapFeed
- Configure NDMA_CAP_FEED_URL only with the authorized feed URL supplied by SACHET or the responsible agency. The app does not guess feed identifiers or scrape undocumented endpoints.
- The adapter only permits HTTPS on sachet.ndma.gov.in and supports RSS item XML or a single CAP alert XML document. It honors ETag validation if the server returns an ETag.

Availability of feeds and access permissions may vary. If you do not have an authorized feed URL, the page will say setup is required.

## Configure

Create or edit your local .env file (it is ignored by git):

    IMD_API_TOKEN=your-issued-token
    # Optional, only if IMD's official docs specify another base:
    # IMD_API_BASE=https://api.imd.gov.in/api/v1
    NDMA_CAP_FEED_URL=https://sachet.ndma.gov.in/your-authorized-feed-url

Alternatively, use .streamlit/secrets.toml:

    IMD_API_TOKEN = "your-issued-token"
    NDMA_CAP_FEED_URL = "https://sachet.ndma.gov.in/your-authorized-feed-url"

Never commit credentials. Restart Streamlit after changing environment variables.

## Run and test

    pip install -r requirements.txt
    streamlit run app.py
    pytest -q

Open Live Government Alerts from the Streamlit multipage navigation, optionally filter by state/district, and click Fetch latest government data. The page shows source connection status, fetched timestamps, record counts, and official links.

## Important limitations

- Requests are on-demand, not continuous background monitoring.
- A successful response with no matching rows is different from a failed or unconfigured source.
- An alert is not a verified local rescue incident. Confirm geography, issue/expiry time, severity and actual impact before creating an incident.
- These integrations do not create incidents, change core/priority.py, assign resources or authorize dispatch.
- Government APIs can require registration, token permissions, rate limits and endpoint access. A live connector can only show real data when valid access is configured.
