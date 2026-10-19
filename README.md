# ResQ-AI — Intelligent Disaster Command Center

AI-assisted emergency **decision-support** prototype for Smart India Hackathon.

One-line pitch: *An AI-assisted emergency decision-support platform that analyzes incoming disaster reports, prioritizes incidents based on severity and human impact, and recommends allocation of limited emergency resources dynamically.*

This is a **hackathon MVP / prototype**. It does **not** replace emergency authorities, does **not** make autonomous life-critical decisions, and uses **simulated incident/resource demo data** (Pune-area coordinates); optional live government weather/disaster alerts are shown separately and require official feed access.

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

- Command Center metrics, priority queue, event log
- Interactive PyDeck map (simulated incidents, teams, hospitals, shelters, roads)
- Live USGS earthquake feed (past 24 hours) and a separate Live Global Disaster Intelligence page using the official GDACS API for earthquakes, tropical cyclones, floods, volcanoes, forest fires, and droughts; source links and fetch timestamps are shown, and successful snapshots are cached for up to five minutes
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
- LOAD DEMO DISASTER for a 3–5 minute walkthrough

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

## Live disaster data

The Command Center displays the public [USGS GeoJSON earthquake feed](https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson) separately from the simulated Pune-area response-planning data. It shows the feed source, last successful fetch time, feed-generation time, event locations/magnitudes, and USGS event links. Feed details are documented in [`docs/LIVE_DATA_FEED.md`](docs/LIVE_DATA_FEED.md).

This first integration covers earthquakes only. Live USGS observations are informational and are not automatically inserted into the simulated incident queue or used to make dispatch recommendations.

## Limitations

- Core incident, resource, hospital, shelter, and road records still use simulated prototype CSV data; USGS and GDACS live hazard feeds are informational and kept separate
- Straight-line distance, not real routed travel time
- Greedy assignment, not a proven global optimum
- IMD/NDMA alerts require valid official feed access; no live ambulance/team availability, hospital capacity, shelter occupancy, or road-closure feed is currently connected
- Image upload is stored for the operator; there is no computer vision
- Not a production government system

## Future scope

Additional official hazard feeds, authorized emergency-service/resource APIs, IoT and satellite layers, traffic/road-closure feeds, real road networks, multilingual reports, computer vision, mobile app, role-based access, PostgreSQL/PostGIS, MIP/CP-SAT optimization, predictive modeling.

## Project layout

See `app.py`, `pages/`, `core/`, `components/`, `data/`, `tests/`.
