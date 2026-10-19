# ResQ-AI expanded platform capabilities

## Included in this branch
- Light, responsive command-centre UI (existing theme).
- Deterministic incident prioritization and explainable recommendations (existing engine; preserved).
- Simulated incident/resource state and operator-entered incident reports.
- Existing USGS earthquake feed and IMD/NDMA adapter integration points.
- Existing grounded ResQ Assistant, read-only MCP tools, and optional Amazon Bedrock briefing.
- Incident workflow page for verification, response statuses, operator notes and event timeline.
- Situation report exports in Markdown, JSON and CSV.
- Optional route estimates through OSRM public demo endpoint, with clear limitations and coordinate/HTTPS validation.
- Operator-triggered SMTP email summary integration; no automatic dispatch/notifications.
- Existing analytics, scenario simulator, resource management, map and live alerts pages.
- Automated tests for exports and routing input validation.

## Setup
Install dependencies with `pip install -r requirements.txt`, copy `.env.example` to `.env`, configure only the services you want, and run `streamlit run app.py`.

## Optional integrations
- IMD: configure an authorized `IMD_API_TOKEN` and the official endpoint only after confirming your access and endpoint details.
- NDMA SACHET/CAP: set `NDMA_CAP_FEED_URL` to an official feed URL available to you.
- LLM: `OPENAI_API_KEY`, `OPENAI_BASE_URL`, and `OPENAI_MODEL` per `core/llm_client.py`.
- Amazon Bedrock: configure AWS credentials with least-privilege IAM permissions, `AWS_REGION`, and `AWS_BEDROCK_MODEL_ID`.
- Email: `RESQ_SMTP_HOST`, `RESQ_SMTP_PORT`, `RESQ_SMTP_FROM`, optional `RESQ_SMTP_USERNAME`/`RESQ_SMTP_PASSWORD`, and `RESQ_ALERT_EMAIL_TO`.
- Routing: optionally set `RESQ_ROUTING_BASE_URL` to an approved HTTPS OSRM-compatible provider. Default is the public OSRM demo endpoint.

## Known limitations / roadmap
- Demo incident/resource inventory remains CSV-backed and session-scoped; no production database or multi-user concurrency.
- Real Alexa+ access is gated. MCP support is a prototype and must be deployed to an authorized remote HTTPS endpoint and secured with the identity/OAuth requirements of the target client.
- SMS, WhatsApp, browser push, geofenced push, automatic refresh and field-device telemetry require separate providers/credentials and are not falsely marked as active.
- No authenticated user roles, immutable external audit store, secure file/object upload, computer vision, validated flood models or authoritative road closure API is included.
- Route estimates are informational and may not know about hazards/closures.
- All AI output is advisory; human coordinators remain responsible for verifying and deciding.

## Safety and data handling
Never commit API keys, passwords, access tokens, reporter contact details, or sensitive location data. Use a secret manager for deployed environments. Live alerts are distinct from operator-reported incidents and must never automatically trigger scoring, assignments, or dispatch.
