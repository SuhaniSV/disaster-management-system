# ResQ-AI — Intelligent Disaster Command Center

AI-assisted emergency **decision-support** prototype for Smart India Hackathon.

One-line pitch: *An AI-assisted emergency decision-support platform that analyzes incoming disaster reports, prioritizes incidents based on severity and human impact, and recommends allocation of limited emergency resources dynamically.*

This is a **hackathon MVP / prototype**. It does **not** replace emergency authorities or make autonomous life-critical decisions. **Live Data Mode is the default** and never fills missing sources with sample data. It shows public live USGS earthquake observations and any configured official IMD/NDMA alerts; operator-entered reports remain session records. Demo Mode is an explicit opt-in for testing and uses simulated Pune-area records.

## Problem

Coordinators must answer, under time pressure:

- Which incidents are active and most urgent — and why?
- How many people are affected, and which cases are medical?
- Which rescue teams, hospitals and shelters can respond?
- What changes if a road is blocked or a team becomes unavailable?

## Solution

ResQ-AI is a Streamlit command center that:

1. Ingests an emergency report
2. Extracts structured facts with an LLM **or** a keyword fallback
3. Scores priority with a transparent deterministic engine (0–100)
4. Estimates prototype straight-line distances
5. Recommends a greedy resource allocation
6. Recalculates when roads, teams or capacity change

The language model never issues the final dispatch. It extracts/classifies. Scoring and pairing are deterministic and explainable.

## Architecture

```
Citizen / operator report
        ↓
AI/NLP extraction (LLM or fallback)
        ↓
Deterministic priority engine
        ↓
Geospatial distance + blocked-road penalty
        ↓
Greedy resource / hospital / shelter recommendation
        ↓
Command Center dashboard + scenario recalculation
```

Data for the MVP: CSV files + in-memory `CommandCenter` state (session). `core/database.py` is the swap point for PostgreSQL later. `database/schema.sql` is reserved.

## Features

- Command Center with source-aware Live Data Mode by default; sample metrics/records appear only when Demo Mode is explicitly selected
- Interactive PyDeck map for records with known coordinates; sample map layers appear only in Demo Mode
- Live USGS earthquake feed (past 24 hours), with source attribution, fetch time, source-generated time, and event-detail links; cached for up to five minutes
- Report Emergency with ANALYZE INCIDENT
- Fallback Analysis Mode when no API key / network / malformed JSON
- Explainable priority breakdown
- Recommended allocation with reasons
- Hospital and shelter capacity
- Scenario Simulator (road blocked, team unavailable, new emergency, hospital squeeze)
- Analytics (Plotly)
- ResQ Assistant chatbot grounded in the current incident/resource snapshot
- Read-only MCP server over Streamable HTTP for Alexa+ track (incident listing, priority explanations, resource/shelter status, live government alert adapter)
- Optional Amazon Bedrock briefing tool for the AWS Builder mini-challenge\n- Live Government Alerts page for IMD district nowcasts/warnings and an authorized NDMA SACHET/CAP feed
- Incident Operations workflow, operator notes and audit timeline
- Situation Reports with Markdown/JSON/CSV exports
- Optional driving route estimates with explicit hazard-routing caveats
- Operator-triggered SMTP situation-summary notifications
- Explicit Demo Mode and prepared flood-city scenario for a 3–5 minute walkthrough

## Tech stack

- Python, Streamlit
- Pandas, PyDeck, Plotly
- Optional OpenAI-compatible LLM (`requests`)
- pytest

## Installation

```bash
git clone <your-fork-url>
cd resq-ai
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

Copy `.env.example` to `.env` (optional). Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` for Streamlit secrets.

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Optional. If missing, Fallback Analysis Mode is used |
| `OPENAI_BASE_URL` | Default `https://api.openai.com/v1` (Groq and others work if compatible) |
| `OPENAI_MODEL` | Default `gpt-4o-mini` |
| `IMD_API_TOKEN` | Optional official IMD API token; see live data guide |
| `NDMA_CAP_FEED_URL` | Optional official authorized SACHET/CAP feed URL |
| `AWS_REGION`, `AWS_BEDROCK_MODEL_ID` | Optional Amazon Bedrock briefing integration |
| `RESQ_ROUTING_BASE_URL` | Optional HTTPS OSRM-compatible routing endpoint |
| `RESQ_SMTP_*`, `RESQ_ALERT_EMAIL_TO` | Optional operator-triggered email notifications |

Never put real keys in source control.

## Live government data\n\nSee [docs/LIVE_GOVERNMENT_DATA.md](docs/LIVE_GOVERNMENT_DATA.md) for IMD token setup, the authorized NDMA SACHET/CAP feed configuration, source status, and limitations. Live alerts are not automatically promoted to incidents and do not change deterministic scores.\n\n## Alexa+ hackathon integration

See [`docs/ALEXA_PLUS_HACKATHON.md`](docs/ALEXA_PLUS_HACKATHON.md) for MCP setup, the Streamable HTTP endpoint, demo script, optional Amazon Bedrock integration, and the limits required for a safe submission. Start the MCP server with `python -m resq_mcp.server`.

## Expanded features and limitations\n\nSee [docs/EXPANDED_PLATFORM.md](docs/EXPANDED_PLATFORM.md) for added operator workflows, export formats, optional routing/email integrations, setup, and production limitations. These additions preserve deterministic priority scoring.\n\n## How to run

```bash
streamlit run app.py
```

Regenerate simulated CSVs:

```bash
python data/generate_demo_data.py
```

Tests:

```bash
pytest
```

## Demo workflow (about 3–5 minutes)

1. Click **LOAD DEMO DISASTER** (sidebar). You should see a flood-city picture: multiple active incidents, limited teams, R-07 blocked.
2. Open **Command Center**: map + priority queue + assignments.
3. Open **Report Incident**. Keep the school-flood text (70 students, medical, blocked road). Click **ANALYZE INCIDENT**.
4. Confirm structured extraction (Flood, medical yes, blocked) and a very high priority with a visible score breakdown.
5. Return to Command Center: the new incident is near the top; a medical-capable resource and hospital/shelter are recommended.
6. Open **Scenario Simulator**. Mark **R03 Unavailable** (scenario C) or block another road. Click **RECALCULATE RESPONSE PLAN**.
7. Show **Before vs after** assignment changes.

## Live data mode and source limitations

Live Data Mode is the default across the app. The Command Center shows the public [USGS GeoJSON earthquake feed](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson) with source and fetch timestamps. IMD and NDMA SACHET/CAP alerts require the official credentials/feed URL described in [`docs/LIVE_GOVERNMENT_DATA.md`](docs/LIVE_GOVERNMENT_DATA.md).

Live hazard alerts are not automatically promoted to verified rescue incidents. The public feeds currently integrated do **not** provide a complete real-time inventory of local incidents, responder locations/availability, hospital beds, shelter occupancy, or road closures. Those panels explicitly report that data as unavailable rather than displaying sample values. Operator-entered reports are session records and must be verified by authorized personnel. Switch to Demo Mode in the sidebar only when you intentionally want sample data for testing.

## Limitations

- Live operational coverage is incomplete; some official feeds require credentials and authorized access
- Straight-line distance, not real routed travel time
- Greedy assignment, not a proven global optimum
- No automatic live feed for responder availability, hospital capacity, shelter occupancy, or traffic/road closures; IMD/NDMA feeds require configuration
- Image upload is stored for the operator; there is no computer vision
- Not a production government system

## Future scope

Live disaster feeds, emergency-service APIs, IoT and satellite layers, weather/traffic APIs, real road networks, multilingual reports, computer vision, mobile app, role-based access, PostgreSQL/PostGIS, MIP/CP-SAT optimization, predictive modeling.

## Project layout

See `app.py`, `pages/`, `core/`, `components/`, `data/`, `tests/`.
