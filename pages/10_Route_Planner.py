from __future__ import annotations
import streamlit as st
from components.session import get_center
from components.theme import page_setup, render_header, render_sidebar
from core.routing import route_estimate

page_setup("Route Planner")
center = get_center()
render_sidebar(center)
render_header(center, "Optional road-route estimates · verify closures before any movement")
st.warning("This planner uses a public demo routing service by default. It may be unavailable, rate-limited, or unaware of current disaster closures. Never use it as the sole basis for emergency routing.")
incidents = [r for r in center.incidents if r.get("lat") is not None and r.get("lon") is not None]
destinations = []
for group, rows in (("Resource", center.resources), ("Hospital", center.hospitals), ("Shelter", center.shelters)):
    for row in rows:
        if row.get("lat") is not None and row.get("lon") is not None:
            destinations.append((f"{group}: {row.get('name') or row.get('id')} ({row.get('id')})", row))
if not incidents or not destinations:
    st.info("The current data bundle does not contain enough valid coordinates for route estimates.")
else:
    labels = [f"{r.get('id')} · {r.get('disaster_type')} · priority {r.get('priority_score',0)}" for r in incidents]
    incident = incidents[labels.index(st.selectbox("Origin incident", labels))]
    destination_label = st.selectbox("Destination", [d[0] for d in destinations])
    destination = destinations[[d[0] for d in destinations].index(destination_label)][1]
    if st.button("Estimate driving route", type="primary"):
        with st.spinner("Requesting route estimate…"):
            result = route_estimate(incident["lat"], incident["lon"], destination["lat"], destination["lon"])
        if result.get("ok"):
            a,b,c = st.columns(3)
            a.metric("Estimated distance", f"{result['distance_km']} km")
            b.metric("Estimated drive time", f"{result['duration_minutes']} min")
            c.metric("Provider", result["provider"])
            st.caption(result["notice"])
            st.link_button("Open provider route", result["source_url"])
        else:
            st.error(result.get("error", "Route estimate unavailable."))
st.markdown("### Route policy")
st.write("- Incident scores are not affected by route estimates.")
st.write("- Known blocked roads are stored in the scenario model, but the public routing API is not guaranteed to know them.")
st.write("- Use an approved local routing/geospatial provider before any real-world deployment.")
