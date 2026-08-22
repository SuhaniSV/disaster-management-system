from __future__ import annotations

from copy import deepcopy

import pandas as pd
import streamlit as st

from components.charts import assignment_table, priority_distribution
from components.session import get_center, persist
from components.theme import page_setup, render_header, render_sidebar
from core.state import load_demo_disaster

page_setup("Scenario Simulator")

center = get_center()
render_sidebar(center)
render_header(
    center,
    "Dynamic reassignment · change roads, teams or capacity, then recalculate the recommended plan",
)

st.warning(
    "This is a prototype what-if tool. Distances are straight-line estimates with a blocked-road detour penalty. "
    "It is not a guaranteed optimal rescue plan."
)

if "sim_before" not in st.session_state:
    st.session_state.sim_before = None
    st.session_state.sim_after = None
    st.session_state.sim_label = ""


def snapshot():
    return {
        "assignments": deepcopy(center.assignments),
        "metrics": center.metrics(),
        "resources": {r["id"]: r.get("status") for r in center.resources},
        "roads": {r["id"]: r.get("status") for r in center.roads},
        "priorities": {i["id"]: i.get("priority_score") for i in center.incidents},
    }


st.markdown("### Prepared scenarios")
a, b, c, d, e = st.columns(5)
if a.button("A · Normal", use_container_width=True):
    persist(load_demo_disaster())
    # Unblock demo constraints for a "normal" picture
    center = get_center()
    center.set_road_status("R-07", "Open")
    for rid in ("R08", "R10"):
        center.set_resource_status(rid, "Available")
    persist(center)
    st.session_state.sim_label = "Scenario A — Normal situation"
    st.rerun()
if b.button("B · Road blocked", use_container_width=True):
    st.session_state.sim_before = snapshot()
    center.set_road_status("R-07", "Blocked")
    persist(center)
    st.session_state.sim_after = snapshot()
    st.session_state.sim_label = "Scenario B — Major road R-07 blocked"
    st.rerun()
if c.button("C · Team unavailable", use_container_width=True):
    st.session_state.sim_before = snapshot()
    target = "R03"
    if any(r.get("id") == target for r in center.resources):
        center.set_resource_status(target, "Unavailable")
    persist(center)
    st.session_state.sim_after = snapshot()
    st.session_state.sim_label = "Scenario C — Rescue Team R03 unavailable"
    st.rerun()
if d.button("D · New emergency", use_container_width=True):
    st.session_state.sim_before = snapshot()
    center.analyze_and_add_incident(
        description=(
            "Flood water has entered a school. Approximately 70 students are trapped. "
            "Two require urgent medical assistance. The main road is blocked."
        ),
        people_affected=70,
        lat=18.5164,
        lon=73.8567,
        accessibility="Blocked",
        reporter="scenario-d",
    )
    persist(center)
    st.session_state.sim_after = snapshot()
    st.session_state.sim_label = "Scenario D — Large new school-flood emergency"
    st.rerun()
if e.button("E · Hospital squeeze", use_container_width=True):
    st.session_state.sim_before = snapshot()
    center.set_hospital_beds("H01", 1)
    center.set_hospital_beds("H02", 2)
    persist(center)
    st.session_state.sim_after = snapshot()
    st.session_state.sim_label = "Scenario E — Hospital capacity decreases"
    st.rerun()

st.markdown("### Manual controls")
c1, c2 = st.columns(2)
with c1:
    road_ids = [r.get("id") for r in center.roads]
    road = st.selectbox("Road", road_ids)
    road_status = st.selectbox("Road status", ["Open", "Blocked"])
    if st.button("Mark road", use_container_width=True):
        st.session_state.sim_before = snapshot()
        center.set_road_status(road, road_status)
        persist(center)
        st.session_state.sim_after = snapshot()
        st.session_state.sim_label = f"Road {road} → {road_status}"
        st.rerun()
    resource_ids = [r.get("id") for r in center.resources]
    resource = st.selectbox("Resource", resource_ids)
    resource_status = st.selectbox("Resource status", ["Available", "Unavailable"])
    if st.button("Mark resource", use_container_width=True):
        st.session_state.sim_before = snapshot()
        center.set_resource_status(resource, resource_status)
        persist(center)
        st.session_state.sim_after = snapshot()
        st.session_state.sim_label = f"Resource {resource} → {resource_status}"
        st.rerun()
with c2:
    inc_ids = [i.get("id") for i in center.incidents if str(i.get("status")).lower() != "resolved"]
    if inc_ids:
        inc = st.selectbox("Incident", inc_ids)
        current = next(i for i in center.incidents if i.get("id") == inc)
        people = st.number_input("People affected", min_value=0, value=int(current.get("people_affected") or 0))
        if st.button("Increase / set people affected", use_container_width=True):
            st.session_state.sim_before = snapshot()
            center.bump_people(inc, int(people))
            persist(center)
            st.session_state.sim_after = snapshot()
            st.session_state.sim_label = f"{inc} people affected → {people}"
            st.rerun()
    hosp_ids = [h.get("id") for h in center.hospitals]
    hid = st.selectbox("Hospital", hosp_ids)
    beds = st.number_input("Available beds", min_value=0, value=0)
    if st.button("Change hospital capacity", use_container_width=True):
        st.session_state.sim_before = snapshot()
        center.set_hospital_beds(hid, int(beds))
        persist(center)
        st.session_state.sim_after = snapshot()
        st.session_state.sim_label = f"Hospital {hid} beds → {beds}"
        st.rerun()
    shel_ids = [s.get("id") for s in center.shelters]
    sid = st.selectbox("Shelter", shel_ids)
    occ = st.number_input("Shelter occupied", min_value=0, value=0)
    if st.button("Change shelter occupancy", use_container_width=True):
        st.session_state.sim_before = snapshot()
        center.set_shelter_occupied(sid, int(occ))
        persist(center)
        st.session_state.sim_after = snapshot()
        st.session_state.sim_label = f"Shelter {sid} occupied → {occ}"
        st.rerun()

if st.button("RECALCULATE RESPONSE PLAN", type="primary", use_container_width=True):
    st.session_state.sim_before = snapshot()
    center.recalculate(reason="Manual recalculation requested")
    persist(center)
    st.session_state.sim_after = snapshot()
    st.session_state.sim_label = "Manual recalculation"
    st.toast("Response plan recalculated")
    st.rerun()

if st.session_state.sim_label:
    st.markdown(f"### Before vs after — {st.session_state.sim_label}")

before = st.session_state.sim_before
after = st.session_state.sim_after
if before and after:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Active incidents", after["metrics"]["active_incidents"], after["metrics"]["active_incidents"] - before["metrics"]["active_incidents"])
    m2.metric("Available resources", after["metrics"]["available_resources"], after["metrics"]["available_resources"] - before["metrics"]["available_resources"])
    m3.metric("Assigned", after["metrics"]["assigned_resources"], after["metrics"]["assigned_resources"] - before["metrics"]["assigned_resources"])
    m4.metric("People affected", after["metrics"]["people_affected"], after["metrics"]["people_affected"] - before["metrics"]["people_affected"])

    left, right = st.columns(2)
    with left:
        st.markdown("**Assignments before**")
        st.dataframe(pd.DataFrame(before["assignments"]), use_container_width=True, hide_index=True)
    with right:
        st.markdown("**Assignments after**")
        st.dataframe(pd.DataFrame(after["assignments"]), use_container_width=True, hide_index=True)

    changes = []
    before_map = {a.get("incident_id"): a.get("resource_id") for a in before["assignments"]}
    after_map = {a.get("incident_id"): a.get("resource_id") for a in after["assignments"]}
    for iid in sorted(set(before_map) | set(after_map)):
        if before_map.get(iid) != after_map.get(iid):
            changes.append(
                {
                    "Incident": iid,
                    "Before": before_map.get(iid) or "Unassigned",
                    "After": after_map.get(iid) or "Unassigned",
                }
            )
    if changes:
        st.success("Recommended allocation changed for the incidents below.")
        st.dataframe(changes, use_container_width=True, hide_index=True)
    else:
        st.info("No pairing changes for this perturbation (priorities or hospitals may still have moved).")

    fig = priority_distribution(center)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
else:
    st.caption("Run a scenario or RECALCULATE RESPONSE PLAN to populate before/after.")

st.markdown("### Current recommended plan")
st.dataframe(assignment_table(center), use_container_width=True, hide_index=True)
