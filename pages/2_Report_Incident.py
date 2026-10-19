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

if center.demo_mode:
    st.info("Demo Mode is active. The form starts with a clearly simulated sample report; edit it for testing only.")
else:
    st.info("Live Data Mode: enter a real operator-observed report and its actual coordinates. The form does not inject a sample incident. Reports remain unverified until an authorized operator confirms them.")
st.caption("The language model (or fallback keyword engine) extracts structured facts. It does not choose the final rescue unit. Priority scoring and assignment are deterministic.")

demo_text = (
    "Flood water has entered a school. Approximately 70 students are trapped. "
    "Two require urgent medical assistance. The main road is blocked."
)

with st.form("report_form"):
    description = st.text_area("Incident description", value=demo_text if center.demo_mode else "", height=140)
    c1, c2, c3 = st.columns(3)
    people = c1.number_input("Estimated people affected", min_value=0, value=70 if center.demo_mode else 0, step=1)
    lat = c2.number_input("Latitude", value=18.5164 if center.demo_mode else 0.0, format="%.4f", help="Enter the actual incident latitude. The live mode does not assume Pune coordinates.")
    lon = c3.number_input("Longitude", value=73.8567 if center.demo_mode else 0.0, format="%.4f", help="Enter the actual incident longitude. The live mode does not assume Pune coordinates.")
    accessibility = st.selectbox("Observed accessibility", ["Open", "Restricted", "Blocked"], index=2)
    reporter = st.text_input("Reporter (optional)", value="field-officer-demo" if center.demo_mode else "")
    image = st.file_uploader("Optional image (stored for operator review only — no computer vision in this MVP)", type=["png", "jpg", "jpeg"])
    submitted = st.form_submit_button("ANALYZE INCIDENT", use_container_width=True)

if submitted:
    errors = validate_report(description, people, lat, lon)
    if not center.demo_mode and float(lat) == 0.0 and float(lon) == 0.0:
        errors.append("Enter the actual incident latitude and longitude; 0,0 is only an empty-field placeholder in Live Data Mode.")
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
        st.success(f"{center.ai_mode}")
        st.json(
            {
                "disaster_type": analysis["disaster_type"],
                "severity": analysis["severity"],
                "people_affected": analysis["people_affected"],
                "medical_emergency": analysis["medical_emergency"],
                "accessibility": analysis["accessibility"],
                "urgency": analysis["urgency"],
            }
        )
        st.markdown(f"### {incident['id']} · Priority {incident.get('priority_score')}/100 · {incident.get('urgency')}")
        for item in incident.get("priority_breakdown") or []:
            st.write(f"{item.get('label')}: +{item.get('points')} ({item.get('detail')})")
        st.write(incident.get("recommended_action") or "")
        if assignment:
            st.write(
                f"Recommended resource: **{assignment.get('resource_id') or 'None available'}** "
                f"({assignment.get('resource_name') or '—'})"
            )
            if assignment.get("distance_km") is not None:
                st.caption(f"Prototype distance {assignment['distance_km']} km. {assignment.get('reason')}")
            st.write(f"Hospital: {assignment.get('hospital_id')} · Shelter: {assignment.get('shelter_id')}")
        st.caption("Open Command Center to see the map and queue update.")

st.divider()
st.caption(f"Default map center is simulated {CITY_LAT}, {CITY_LON} (Pune area). All reports in this MVP are prototype data.")
