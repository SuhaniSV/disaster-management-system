from __future__ import annotations

from copy import deepcopy

import pandas as pd
import streamlit as st

from components.session import get_center
from components.theme import page_setup, render_header, render_sidebar
from core.database import load_demo_bundle
from core.state import CommandCenter

page_setup("Scenario Simulator")

live_center = get_center()
render_sidebar(live_center)
render_header(
    live_center,
    "Test operational changes and compare the recommended response before and after recalculation",
)

st.warning(
    "Decision-support prototype only. Distances are straight-line estimates with a blocked-road penalty; "
    "recommendations are not dispatch confirmations or guaranteed travel times."
)

# Keep what-if changes isolated from the operational command center. The CSV assets
# are simulated inventory for testing, never live dispatch resources.
if st.session_state.get("simulator_version") != 2:
    st.session_state.simulator_version = 2
    st.session_state.sim_before = None
    st.session_state.sim_after = None
    st.session_state.sim_label = ""
    st.session_state.sim_center = None

if st.session_state.sim_center is None:
    inventory = load_demo_bundle()
    has_live_incidents = bool(live_center.incidents)
    incidents = deepcopy(live_center.incidents) if has_live_incidents else deepcopy(inventory.get("incidents", []))
    st.session_state.sim_center = CommandCenter(
        bundle={
            "incidents": incidents,
            "resources": deepcopy(inventory.get("resources", [])),
            "hospitals": deepcopy(inventory.get("hospitals", [])),
            "shelters": deepcopy(inventory.get("shelters", [])),
            "roads": deepcopy(inventory.get("roads", [])),
            "events": [],
        }
    )
    st.session_state.sim_data_source = (
        "Using current incident reports with simulated test inventory."
        if has_live_incidents
        else "No current incident reports were found; using a fully simulated example scenario."
    )

center = st.session_state.sim_center


def snapshot():
    return {
        "assignments": deepcopy(center.assignments),
        "metrics": center.metrics(),
        "resources": {r["id"]: r.get("status") for r in center.resources},
        "roads": {r["id"]: r.get("status") for r in center.roads},
        "priorities": {i["id"]: i.get("priority_score") for i in center.incidents},
    }


def assignment_rows(rows):
    """Convert raw allocation records into a compact, readable comparison table."""
    output = []
    for row in rows or []:
        resource_id = row.get("resource_id")
        distance = row.get("distance_km")
        output.append(
            {
                "Incident": row.get("incident_id") or "Unknown",
                "Allocation": "Assigned" if resource_id else "Unassigned",
                "Resource": (
                    f'{row.get("resource_name") or "Unnamed resource"} ({resource_id})'
                    if resource_id else "—"
                ),
                "Distance": f"{distance:.2f} km" if isinstance(distance, (int, float)) else "—",
                "Why": row.get("reason") or "No allocation explanation available.",
                "Hospital": row.get("hospital_name") or row.get("hospital_id") or "—",
                "Shelter": row.get("shelter_name") or row.get("shelter_id") or "—",
            }
        )
    return output


def show_assignment_table(title, rows):
    st.markdown(f"**{title}**")
    formatted = assignment_rows(rows)
    if formatted:
        st.dataframe(pd.DataFrame(formatted), use_container_width=True, hide_index=True)
    else:
        st.info("No active incident assignments to compare.")


st.markdown("### What-if scenarios")
st.caption("Sandbox only — resource teams, roads, hospitals and shelters are simulated test records, not live verified assets and must not be used as dispatch instructions.")
st.info(st.session_state.sim_data_source)
a, b, c, d, e = st.columns(5)
if a.button("A · Reset scenario", use_container_width=True):
    inventory = load_demo_bundle()
    incidents = deepcopy(live_center.incidents) if live_center.incidents else deepcopy(inventory.get("incidents", []))
    st.session_state.sim_center = CommandCenter(
        bundle={
            "incidents": incidents,
            "resources": deepcopy(inventory.get("resources", [])),
            "hospitals": deepcopy(inventory.get("hospitals", [])),
            "shelters": deepcopy(inventory.get("shelters", [])),
            "roads": deepcopy(inventory.get("roads", [])),
            "events": [],
        }
    )
    st.session_state.sim_before = None
    st.session_state.sim_after = None
    st.session_state.sim_label = ""
    st.rerun()
if b.button("B · Road blocked", use_container_width=True):
    st.session_state.sim_before = snapshot()
    if any(r.get("id") == "R-07" for r in center.roads):
        center.set_road_status("R-07", "Blocked")
    else:
        st.warning("This scenario requires road record R-07. No road was changed.")
    st.session_state.sim_after = snapshot()
    st.session_state.sim_label = "Scenario B — Road blockage"
    st.rerun()
if c.button("C · Team unavailable", use_container_width=True):
    st.session_state.sim_before = snapshot()
    if any(r.get("id") == "R03" for r in center.resources):
        center.set_resource_status("R03", "Unavailable")
    else:
        st.warning("This scenario requires resource record R03. No resource was changed.")
    st.session_state.sim_after = snapshot()
    st.session_state.sim_label = "Scenario C — Resource unavailable"
    st.rerun()
if d.button("D · New emergency", use_container_width=True):
    st.session_state.sim_before = snapshot()
    center.analyze_and_add_incident(
        description=(
            "SAMPLE SCENARIO ONLY: Flood water has entered a school. Approximately 70 students "
            "are trapped. Two require urgent medical assistance. The main road is blocked."
        ),
        people_affected=70,
        lat=18.5164,
        lon=73.8567,
        accessibility="Blocked",
        reporter="scenario-sample",
    )
    st.session_state.sim_after = snapshot()
    st.session_state.sim_label = "Scenario D — Sample school-flood emergency"
    st.rerun()
if e.button("E · Hospital squeeze", use_container_width=True):
    st.session_state.sim_before = snapshot()
    changed = False
    for hid, beds in (("H01", 1), ("H02", 2)):
        if any(h.get("id") == hid for h in center.hospitals):
            center.set_hospital_beds(hid, beds)
            changed = True
    if not changed:
        st.warning("This scenario requires hospital records H01 or H02. No capacity was changed.")
    st.session_state.sim_after = snapshot()
    st.session_state.sim_label = "Scenario E — Reduced hospital capacity"
    st.rerun()

st.markdown("### Manual controls")
st.caption("Changes here affect only this sandbox. They do not update live incident records or dispatch real teams.")

c1, c2 = st.columns(2)
with c1:
    road_ids = [r.get("id") for r in center.roads if r.get("id")]
    road = st.selectbox("Road", road_ids, disabled=not road_ids, placeholder="No roads in sandbox")
    road_status = st.selectbox("Road status", ["Open", "Blocked"])
    if st.button("Apply road status", use_container_width=True, disabled=not road_ids):
        st.session_state.sim_before = snapshot()
        center.set_road_status(road, road_status)
        st.session_state.sim_after = snapshot()
        st.session_state.sim_label = f"Road {road} → {road_status}"
        st.rerun()

    resource_ids = [r.get("id") for r in center.resources if r.get("id")]
    resource = st.selectbox("Resource", resource_ids, disabled=not resource_ids, placeholder="No resources in sandbox")
    resource_status = st.selectbox("Resource status", ["Available", "Unavailable"])
    if st.button("Apply resource status", use_container_width=True, disabled=not resource_ids):
        st.session_state.sim_before = snapshot()
        center.set_resource_status(resource, resource_status)
        st.session_state.sim_after = snapshot()
        st.session_state.sim_label = f"Resource {resource} → {resource_status}"
        st.rerun()

with c2:
    inc_ids = [i.get("id") for i in center.incidents if str(i.get("status")).lower() != "resolved" and i.get("id")]
    inc = st.selectbox("Incident", inc_ids, disabled=not inc_ids, placeholder="No active incidents")
    current = next((i for i in center.incidents if i.get("id") == inc), {}) if inc else {}
    people = st.number_input(
        "People affected",
        min_value=0,
        value=int(current.get("people_affected") or 0),
        disabled=not bool(inc),
    )
    if st.button("Update people affected", use_container_width=True, disabled=not bool(inc)):
        st.session_state.sim_before = snapshot()
        center.bump_people(inc, int(people))
        st.session_state.sim_after = snapshot()
        st.session_state.sim_label = f"{inc} · people affected updated"
        st.rerun()

    hosp_ids = [h.get("id") for h in center.hospitals if h.get("id")]
    hid = st.selectbox("Hospital", hosp_ids, disabled=not hosp_ids, placeholder="No hospitals in sandbox")
    hospital = next((h for h in center.hospitals if h.get("id") == hid), {}) if hid else {}
    beds = st.number_input(
        "Available beds",
        min_value=0,
        value=int(hospital.get("available_beds") or 0),
        disabled=not bool(hid),
    )
    if st.button("Update hospital capacity", use_container_width=True, disabled=not hosp_ids):
        st.session_state.sim_before = snapshot()
        center.set_hospital_beds(hid, int(beds))
        st.session_state.sim_after = snapshot()
        st.session_state.sim_label = f"Hospital {hid} · available beds updated"
        st.rerun()

    shelter_ids = [s.get("id") for s in center.shelters if s.get("id")]
    sid = st.selectbox("Shelter", shelter_ids, disabled=not shelter_ids, placeholder="No shelters in sandbox")
    shelter = next((s for s in center.shelters if s.get("id") == sid), {}) if sid else {}
    occ = st.number_input(
        "Shelter occupied",
        min_value=0,
        value=int(shelter.get("occupied") or 0),
        disabled=not bool(sid),
    )
    if st.button("Update shelter occupancy", use_container_width=True, disabled=not shelter_ids):
        st.session_state.sim_before = snapshot()
        center.set_shelter_occupied(sid, int(occ))
        st.session_state.sim_after = snapshot()
        st.session_state.sim_label = f"Shelter {sid} · occupancy updated"
        st.rerun()

if st.button("RECALCULATE RESPONSE PLAN", type="primary", use_container_width=True):
    st.session_state.sim_before = snapshot()
    center.recalculate(reason="Manual recalculation requested")
    st.session_state.sim_after = snapshot()
    st.session_state.sim_label = "Manual recalculation"
    st.rerun()

if st.session_state.sim_label:
    st.markdown(f"### Before vs after — {st.session_state.sim_label}")

before = st.session_state.sim_before
after = st.session_state.sim_after
if before and after:
    st.markdown("#### Operational impact")
    metrics = [
        ("Active incidents", "active_incidents"),
        ("Available resources", "available_resources"),
        ("Assigned resources", "assigned_resources"),
        ("People affected", "people_affected"),
    ]
    metric_cols = st.columns(4)
    for col, (label, key) in zip(metric_cols, metrics):
        old_value = before["metrics"].get(key, 0)
        new_value = after["metrics"].get(key, 0)
        col.markdown(f"**{label}**")
        col.markdown(f"<div class='resq-metric-value'>{old_value:,} <span style='color:#64748b'>→</span> {new_value:,}</div>", unsafe_allow_html=True)

    before_assignments = before.get("assignments", [])
    after_assignments = after.get("assignments", [])
    left, right = st.columns(2)
    with left:
        show_assignment_table("Assignments before", before_assignments)
    with right:
        show_assignment_table("Assignments after", after_assignments)

    before_map = {a.get("incident_id"): a.get("resource_id") for a in before_assignments}
    after_map = {a.get("incident_id"): a.get("resource_id") for a in after_assignments}
    changes = []
    for iid in sorted(set(before_map) | set(after_map)):
        old_resource = before_map.get(iid)
        new_resource = after_map.get(iid)
        if old_resource != new_resource:
            changes.append(
                {
                    "Incident": iid,
                    "Before": old_resource or "Unassigned",
                    "After": new_resource or "Unassigned",
                }
            )
    if changes:
        st.success("The recommended allocation changed for these incidents.")
        st.dataframe(pd.DataFrame(changes), use_container_width=True, hide_index=True)
    elif not center.resources:
        st.info("No resource records exist in this sandbox, so allocation comparison is unavailable.")
    else:
        st.info(
            "No incident-to-resource pairing changed. Review the reasons in the tables above; "
            "priority or hospital recommendations can change even when the assigned resource does not."
        )

st.markdown("### Current simulated recommendation")
current_rows = assignment_rows(center.assignments)
if current_rows:
    st.dataframe(pd.DataFrame(current_rows), use_container_width=True, hide_index=True)
else:
    st.info("No active incidents are available in this scenario. Reset the scenario to reload its starting data.")
