from __future__ import annotations

import pandas as pd
import streamlit as st

from components.session import get_center, persist
from components.theme import page_setup, render_header, render_sidebar
from core.official_directory import nearby_public_hospitals
from core.persistence import (
    inventory_admin_configured,
    inventory_admin_token_matches,
    is_configured,
    save_inventory,
)

page_setup("Scenario Simulator")

center = get_center()
render_sidebar(center)
render_header(
    center,
    "Assess reported emergencies and review resource readiness using records actually available to ResQ-AI",
)

st.caption(
    "This page uses operator-submitted incidents only. It does not create sample incidents or treat "
    "unverified assets as real. An assessment is not a dispatch confirmation."
)

# Make the persistence state visible so operators know whether reports survive a new session.
if st.session_state.get("incident_store_error"):
    st.error(str(st.session_state["incident_store_error"]))
elif st.session_state.get("incident_store_configured"):
    st.success("Incident database: configured for permanent storage.")
else:
    st.warning("Incident database: not connected. Reports may exist only in this browser session.")


def _parse_inventory(upload, kind: str) -> list[dict]:
    if upload is None:
        return []
    frame = pd.read_csv(upload).fillna("")
    required = {
        "resources": {"id", "name", "type", "lat", "lon", "status", "capacity", "capabilities"},
        "hospitals": {"id", "name", "lat", "lon", "available_beds", "emergency_capability"},
        "shelters": {"id", "name", "lat", "lon", "capacity", "occupied"},
    }[kind]
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{kind.title()} CSV is missing columns: {', '.join(missing)}")
    rows = []
    for row in frame.to_dict(orient="records"):
        record = {str(k): v for k, v in row.items()}
        record["id"] = str(record.get("id") or "").strip()
        record["name"] = str(record.get("name") or "").strip()
        if not record["id"] or not record["name"]:
            raise ValueError(f"Every {kind[:-1]} record needs a non-empty id and name.")
        record["lat"], record["lon"] = float(record["lat"]), float(record["lon"])
        if not (-90 <= record["lat"] <= 90 and -180 <= record["lon"] <= 180):
            raise ValueError(f"Invalid coordinates in {kind} record {record['id']}.")
        if kind == "resources":
            record["capacity"] = int(float(record["capacity"]))
            record["status"] = str(record["status"]).strip().title()
            if record["status"] not in {"Available", "Idle", "Standby", "Busy", "Unavailable"}:
                raise ValueError(f"Unsupported status in resource {record['id']}.")
            record["type"] = str(record["type"]).strip().lower()
            record["capabilities"] = str(record["capabilities"]).strip()
            record["source"] = "operator-verified-upload"
            record["availability_status"] = "operator-reported"
        elif kind == "hospitals":
            record["available_beds"] = int(float(record["available_beds"]))
            record["emergency_capability"] = str(record["emergency_capability"]).strip()
            record["source"] = "operator-verified-upload"
            record["source_type"] = "operator_verified_inventory"
            record["availability_status"] = "operator-reported"
        else:
            record["capacity"] = int(float(record["capacity"]))
            record["occupied"] = int(float(record["occupied"]))
            record["source"] = "operator-verified-upload"
        rows.append(record)
    return rows


st.markdown("### Connect operational inventory")
st.caption(
    "Upload current records supplied by authorized response and hospital partners. "
    "The allocator uses team status, coordinates, capacity and capabilities. "
    "Never upload example/demo records or private patient information."
)
if not inventory_admin_configured():
    st.warning(
        "Inventory management is locked because INVENTORY_ADMIN_TOKEN is not configured. "
        "Add this secret in Streamlit Community Cloud settings before enabling uploads."
    )
elif not st.session_state.get("inventory_admin_authenticated", False):
    token_candidate = st.text_input("Inventory operator access token", type="password", key="inventory_admin_token_input")
    if st.button("Unlock inventory management", key="unlock_inventory_management"):
        if inventory_admin_token_matches(token_candidate):
            st.session_state.inventory_admin_authenticated = True
            st.success("Inventory management unlocked for this session.")
            st.rerun()
        else:
            st.error("The inventory access token is incorrect.")
if inventory_admin_configured() and st.session_state.get("inventory_admin_authenticated", False):
    with st.expander("CSV format and inventory upload", expanded=not center.resources):
        st.markdown(
            "**Rescue teams/resources** — id,name,type,lat,lon,status,capacity,capabilities\n\n"
            "Type examples: rescue_team, medical_rescue, ambulance, fire_response. "
            "Status must be Available, Idle, Standby, Busy, or Unavailable.\n\n"
            "**Hospitals** — id,name,lat,lon,available_beds,emergency_capability (yes/no/unknown).\n\n"
            "**Shelters** — id,name,lat,lon,capacity,occupied."
        )
        resource_upload = st.file_uploader("Rescue-team / ambulance inventory CSV", type=["csv"], key="resource_inventory_upload")
        hospital_upload = st.file_uploader("Verified hospital capacity CSV", type=["csv"], key="hospital_inventory_upload")
        shelter_upload = st.file_uploader("Shelter capacity CSV", type=["csv"], key="shelter_inventory_upload")
        if st.button("Save and recalculate inventory", type="primary", use_container_width=True):
            try:
                new_resources = _parse_inventory(resource_upload, "resources") if resource_upload else []
                new_hospitals = _parse_inventory(hospital_upload, "hospitals") if hospital_upload else []
                new_shelters = _parse_inventory(shelter_upload, "shelters") if shelter_upload else []
                if not any([new_resources, new_hospitals, new_shelters]):
                    st.warning("Choose at least one inventory CSV before saving.")
                else:
                    for attr, incoming in (
                        ("resources", new_resources),
                        ("hospitals", new_hospitals),
                        ("shelters", new_shelters),
                    ):
                        if incoming:
                            current = {str(item.get("id")): item for item in getattr(center, attr)}
                            current.update({str(item["id"]): item for item in incoming})
                            setattr(center, attr, list(current.values()))
                    center.recalculate(reason="Operator inventory uploaded; allocations recalculated")
                    persist(center)
                    if is_configured():
                        save_inventory({
                            "resources": new_resources,
                            "hospitals": new_hospitals,
                            "shelters": new_shelters,
                        })
                        st.success("Inventory saved to Supabase and allocation recalculated.")
                    else:
                        st.warning("Inventory is active for this app session only. Configure DATABASE_URL and run migrations/002_operational_inventory.sql for persistence.")
                    st.rerun()
            except (ValueError, TypeError, KeyError, pd.errors.ParserError) as exc:
                st.error(f"Inventory was not saved: {exc}")
            except Exception as exc:
                st.error(
                    f"Inventory persistence failed ({type(exc).__name__}). Run "
                    "migrations/002_operational_inventory.sql in Supabase; records remain session-only."
                )

if st.session_state.get("inventory_store_error"):
    st.warning(str(st.session_state["inventory_store_error"]))

active_incidents = [
    incident for incident in center.incidents
    if str(incident.get("status") or "").strip().lower() != "resolved"
]

if not active_incidents:
    st.info(
        "No incidents reported yet. Submit an incident through Report Incident to generate an assessment. "
        "No incident, distance, rescue team, hospital, or recommendation will be invented."
    )
    st.stop()

incident_labels = {
    str(item.get("id")): (
        f'{item.get("id")} · {item.get("disaster_type") or "Unclassified"} · '
        f'{item.get("people_affected") or 0:,} people affected'
    )
    for item in active_incidents
    if item.get("id")
}
incident_ids = list(incident_labels)
if not incident_ids:
    st.warning("Incident records were loaded, but none has a usable ID. Please review the saved report.")
    st.stop()

st.markdown("### Reported incident")
selected_id = st.selectbox(
    "Choose a reported incident",
    incident_ids,
    format_func=lambda value: incident_labels[value],
)
incident = next((item for item in active_incidents if str(item.get("id")) == selected_id), {})

# Automatically look up nearby public hospital facilities from the India hospital
# directory. These are location references only, not live bed/dispatch availability.
verified_hospitals = [
    h for h in center.hospitals
    if str(h.get("source_type") or "") != "public_reference_directory"
]
public_hospitals, hospital_lookup_error = nearby_public_hospitals(incident.get("lat"), incident.get("lon"))
center.hospitals = verified_hospitals + public_hospitals
center.recalculate(reason="Refreshed nearby hospital reference matches for selected incident")
assignment = center.assignment_for(selected_id)

raw_type = str(incident.get("disaster_type") or "").strip()
is_unclassified = not raw_type or raw_type.lower() in {"unknown", "unclassified", "none", "null"}
incident_type = "Unclassified — review the report details" if is_unclassified else raw_type
people = incident.get("people_affected")
try:
    people_label = f"{int(people):,}" if people is not None and str(people).strip() else "Not provided"
except (TypeError, ValueError):
    people_label = str(people or "Not provided")
lat, lon = incident.get("lat"), incident.get("lon")
location = (
    f"{lat}, {lon}"
    if lat is not None and lon is not None
    else "Location coordinates not available"
)

a, b, c, d = st.columns(4)
score = incident.get("priority_score")
a.metric("Priority score", f"{score}/100" if score is not None else "Not calculated")
b.metric("People affected", people_label)
c.metric("Incident type", incident_type)
d.metric("Status", str(incident.get("status") or "Active"))

st.markdown("**Reported description**")
description = str(incident.get("description") or incident.get("summary") or "").strip()
if description:
    st.write(description)
else:
    st.warning("This saved incident has no description. Review the original report; the hazard type cannot be verified from this record.")

detail_left, detail_right = st.columns(2)
with detail_left:
    st.markdown("**Reported location**")
    st.write(location)
with detail_right:
    st.markdown("**Reported at**")
    st.write(str(incident.get("reported_at") or "Timestamp not available"))

if is_unclassified:
    st.warning(
        "The saved report is not classified as a known hazard. ResQ-AI will not guess the incident type. "
        "Review or resubmit the report with the hazard and location clearly described."
    )

st.markdown("### General response guidance")
action = str(incident.get("recommended_action") or "").strip()
if action:
    st.info(action.replace("Recommended action:", "Suggested guidance:", 1))
    st.caption("Guidance only — this does not confirm a dispatch or verify on-scene conditions.")
else:
    st.info("No response guidance has been generated for this report yet.")

if assignment and assignment.get("reason"):
    st.caption(str(assignment["reason"]))

st.markdown("### Resource readiness")
st.caption(
    "Incident assessment and resource availability are separate. A priority score can be calculated "
    "without a verified rescue-team, hospital, medicine, or shelter inventory."
)

counts = {
    "Active reported incidents": len(active_incidents),
    "Verified resource records loaded": len(center.resources),
    "Verified hospital capacity records": len(verified_hospitals),
    "Nearby public hospital matches": len(public_hospitals),
    "Shelter records loaded": len(center.shelters),
}
cols = st.columns(len(counts))
for col, (label, count) in zip(cols, counts.items()):
    col.metric(label, count)

if not center.resources:
    st.error(
        "Resource allocation unavailable: no verified rescue-team inventory is connected. "
        "No team name, distance, ambulance, or medication availability can be recommended until "
        "real resource records or a trusted live feed is configured."
    )
elif not assignment or not assignment.get("resource_id"):
    st.warning(
        "No eligible nearby resource has been assigned from the currently loaded records. "
        "Check verified resource coordinates, capabilities, capacity, and current availability."
    )
else:
    resource_id = assignment.get("resource_id")
    resource_name = assignment.get("resource_name")
    distance = assignment.get("distance_km")
    if resource_id and resource_name and isinstance(distance, (int, float)):
        st.success(f"Candidate resource: {resource_name} ({resource_id}) · {distance:.2f} km")
        st.caption("This is a decision-support candidate, not a confirmed dispatch.")

if assignment and (assignment.get("hospital_name") or assignment.get("hospital_id")):
    hospital_name = str(assignment.get("hospital_name") or assignment.get("hospital_id"))
    hospital_distance = assignment.get("hospital_km")
    if assignment.get("hospital_availability") == "capacity-reported":
        st.success(
            f"Hospital candidate with operator-reported capacity: {hospital_name}"
            + (f" · {hospital_distance:.2f} km" if isinstance(hospital_distance, (int, float)) else "")
        )
        st.caption("Capacity is operator-reported and must be confirmed by the hospital before transfer.")
    else:
        st.info(
            f"Nearby hospital directory lead: {hospital_name}"
            + (f" · {hospital_distance:.2f} km" if isinstance(hospital_distance, (int, float)) else "")
        )
        st.warning(
            "This is a public facility-directory match, not a verified available bed or dispatch destination. "
            "Call the facility to confirm emergency capability and current capacity."
        )
elif hospital_lookup_error:
    st.warning(hospital_lookup_error)
elif not public_hospitals and not verified_hospitals:
    st.warning(
        "No nearby hospital facility was returned for these coordinates. Verify the incident location "
        "or upload a current hospital inventory from an authorized source."
    )
else:
    st.info("Hospital records were found, but none is eligible for the current recommendation.")

if center.shelters and assignment and (assignment.get("shelter_name") or assignment.get("shelter_id")):
    st.write("**Shelter candidate:** " + str(assignment.get("shelter_name") or assignment.get("shelter_id")))
elif not center.shelters:
    st.caption("No verified shelter inventory is connected.")
