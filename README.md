# ResQ-AI — Intelligent Disaster Command Center

AI-assisted emergency **decision-support** prototype for Smart India Hackathon.

One-line pitch: *An AI-assisted emergency decision-support platform that analyzes incoming disaster reports, prioritizes incidents based on severity and human impact, and recommends allocation of limited emergency resources dynamically.*

This is a **hackathon MVP / prototype**. It does **not** replace emergency authorities, does **not** make autonomous life-critical decisions, and uses **simulated demo data** (Pune-area coordinates), not live government feeds.

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
- Live USGS earthquake feed (past 24 hours), with source attribution, fetch time, source-generated time, and event-detail links; cached for up to five minutes
- Report Emergency with ANALYZE INCIDENT
- Fallback Analysis Mode when no API key / network / malformed JSON
- Explainable priority breakdown
- Recommended allocation with reasons
- Hospital and shelter capacity
- Scenario Simulator (road blocked, team unavailable, new emergency, hospital squeeze)
- Analytics (Plotly)
- ResQ Assistant chatbot grounded in the current incident/resource snapshot
- Read-only MCP server over Streamable HTTP for Alexa+ track (incident listing, priority explanations, resource and shelter status)
- Optional Amazon Bedrock briefing tool for the AWS Builder mini-challenge
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

Never put real keys in source control.

## Alexa+ hackathon integration

See [`docs/ALEXA_PLUS_HACKATHON.md`](docs/ALEXA_PLUS_HACKATHON.md) for MCP setup, the Streamable HTTP endpoint, demo script, optional Amazon Bedrock integration, and the limits required for a safe submission. Start the MCP server with `python -m resq_mcp.server`.

## How to run

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

- Simulated / prototype data only
- Straight-line distance, not real routed travel time
- Greedy assignment, not a proven global optimum
- No live NDMA/IMD/traffic/IoT feeds
- Image upload is stored for the operator; there is no computer vision
- Not a production government system

## Future scope

Live disaster feeds, emergency-service APIs, IoT and satellite layers, weather/traffic APIs, real road networks, multilingual reports, computer vision, mobile app, role-based access, PostgreSQL/PostGIS, MIP/CP-SAT optimization, predictive modeling.

## Project layout

See `app.py`, `pages/`, `core/`, `components/`, `data/`, `tests/`.
