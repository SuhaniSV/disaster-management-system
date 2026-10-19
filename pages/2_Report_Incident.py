from __future__ import annotations

import streamlit as st

from components.session import get_center, persist
from components.theme import page_setup, render_header, render_sidebar
from core.config import CITY_LAT, CITY_LON
from utils.validation import validate_report

page_setup("Report Incident")

center = get_center()
render_sidebar(center)
render_header(center, "Submit an emergency report · NLP extracts facts · the priority engine scores independently")

st.info(
    "The language model (or fallback keyword engine) extracts structured facts. "
    "It does not choose the final rescue unit. Priority scoring and assignment are deterministic."
)

with st.form("report_form"):
    description = st.text_area("Incident description", placeholder="Describe what happened, exact location, hazards, and people affected", height=140)
    c1, c2, c3 = st.columns(3)
    people = c1.number_input("Estimated people affected", min_value=0, value=0, step=1)
    lat = c2.number_input("Latitude", value=0.0, format="%.4f")
    lon = c3.number_input("Longitude", value=0.0, format="%.4f")
    accessibility = st.selectbox("Observed accessibility", ["Open", "Restricted", "Blocked"], index=0)
    reporter = st.text_input("Reporter (optional)", placeholder="Name or call sign")
    image = st.file_uploader("Optional image (stored for operator review only — no computer vision in this MVP)", type=["png", "jpg", "jpeg"])
    submitted = st.form_submit_button("ANALYZE INCIDENT", use_container_width=True)

if submitted:
    errors = validate_report(description, people, lat, lon)
    if errors:
        for err in errors:
            st.error(err)
    else:
        image_name = image.name if image is not None else ""
        with st.status("Analyzing incident…", expanded=True) as status:
            st.write("Running NLP extraction (LLM if configured, otherwise fallback)…")
            result = center.analyze_and_add_incident(
                description=description,
                people_affected=int(people),
                lat=float(lat),
                lon=float(lon),
                accessibility=accessibility,
                reporter=reporter,
                image_name=image_name,
            )
            persist(center)
            status.update(label="Analysis complete", state="complete")
        analysis = result["analysis"]
        incident = result["incident"]
        assignment = result["assignment"]
        st.toast(f"{incident['id']} added to the command queue")

        st.success(f"Analysis complete · {center.ai_mode}")

        # Human-readable incident summary; raw structured output stays optional.
        st.markdown("### Incident assessment")
        score = int(incident.get("priority_score") or 0)
        urgency = str(incident.get("urgency") or "Unknown")
        urgency_color = {
            "Critical": "#e11d48",
            "High": "#ea580c",
            "Medium": "#ca8a04",
            "Low": "#0d9488",
        }.get(urgency, "#64748b")

        st.markdown(
            f"""
            <div style="
                padding:18px 20px; border-radius:16px;
                border:1px solid {urgency_color}55;
                background:linear-gradient(115deg,{urgency_color}14,rgba(20,184,166,.06));
                margin:4px 0 16px;">
              <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;">
                <div>
                  <div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;opacity:.72;">Incident ID</div>
                  <div style="font-size:25px;font-weight:750;">{incident['id']}</div>
                </div>
                <div style="text-align:right;">
                  <div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;opacity:.72;">Priority score</div>
                  <div style="font-size:28px;font-weight:800;color:{urgency_color};">{score}<span style="font-size:15px;opacity:.7;"> / 100</span></div>
                  <span style="display:inline-block;padding:4px 10px;border-radius:999px;background:{urgency_color}20;color:{urgency_color};font-weight:700;font-size:12px;">{urgency.upper()}</span>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        fact_cols = st.columns(3)
        fact_cols[0].metric("Disaster type", str(analysis.get("disaster_type") or "Unknown"))
        fact_cols[1].metric("Severity", f"{analysis.get('severity', '—')}/5")
        fact_cols[2].metric("People affected", f"{analysis.get('people_affected', people):,}")

        fact_cols = st.columns(3)
        fact_cols[0].metric(
            "Medical emergency",
            "Detected" if analysis.get("medical_emergency") else "Not detected",
        )
        fact_cols[1].metric("Access", str(analysis.get("accessibility") or accessibility))
        fact_cols[2].metric("Vulnerable people", f"{incident.get('vulnerable_population') or 0:,}")

        st.markdown("### Why this priority?")
        st.caption("The score is calculated by predefined rules. It is decision support, not an automatic dispatch decision.")
        for item in incident.get("priority_breakdown") or []:
            label = str(item.get("label") or "Factor")
            points = int(item.get("points") or 0)
            detail = str(item.get("detail") or "")
            col_label, col_points = st.columns([5, 1])
            col_label.markdown(f"**{label}**")
            col_label.caption(detail)
            col_points.markdown(f"**+{points}**")
            st.progress(min(100, max(0, points * 3)), text=f"{points} points")

        action = incident.get("recommended_action") or "No recommended action available."
        st.markdown("### Recommended response")
        st.info(action)

        if assignment:
            st.markdown("### Resource and destination recommendation")
            rec_cols = st.columns(3)
            rec_cols[0].metric(
                "Recommended resource",
                str(assignment.get("resource_id") or "Unassigned"),
                help=str(assignment.get("resource_name") or ""),
            )
            rec_cols[1].metric("Hospital", str(assignment.get("hospital_id") or "None"))
            rec_cols[2].metric("Shelter", str(assignment.get("shelter_id") or "None"))
            if assignment.get("distance_km") is not None:
                st.caption(
                    f"Prototype distance: {assignment['distance_km']} km. "
                    f"{assignment.get('reason') or ''}"
                )
            st.caption("A coordinator must verify the recommendation before operational use.")
        else:
            st.warning("No resource assignment is currently available. A coordinator should review the incident.")

        with st.expander("View extracted structured data (JSON)", expanded=False):
            st.caption("Technical view for debugging and review. This is data, not executable code.")
            st.json(
                {
                    "disaster_type": analysis.get("disaster_type"),
                    "severity": analysis.get("severity"),
                    "people_affected": analysis.get("people_affected"),
                    "medical_emergency": analysis.get("medical_emergency"),
                    "accessibility": analysis.get("accessibility"),
                    "urgency": incident.get("urgency"),
                    "vulnerable_population": incident.get("vulnerable_population", 0),
                }
            )

        st.caption("Open Command Center to see the map and priority queue update.")

st.divider()
st.caption(f"Default map center: {CITY_LAT}, {CITY_LON}. Confirm the coordinates before submitting. Reports entered here are operator-submitted and are not independently verified.")
