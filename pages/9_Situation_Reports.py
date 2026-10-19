from __future__ import annotations
import streamlit as st
from components.session import get_center
from components.theme import page_setup, render_header, render_sidebar
from core.reporting import incidents_csv, event_log_csv, json_report, situation_report_markdown

page_setup("Situation Reports")
center = get_center()
render_sidebar(center)
render_header(center, "Exportable operational picture · source-labelled prototype data")
st.info("Exports describe the current in-memory command-center snapshot. Live government alerts are not automatically mixed into incident reports.")
m = center.metrics()
a,b,c,d = st.columns(4)
a.metric("Active incidents", m.get("active_incidents", 0))
b.metric("Critical", m.get("critical_incidents", 0))
c.metric("Available resources", m.get("available_resources", 0))
d.metric("Shelter spaces", m.get("shelter_spaces_available", 0))
st.markdown("### Download reports")
st.download_button("Situation report (Markdown)", situation_report_markdown(center), "resq_situation_report.md", "text/markdown", use_container_width=True)
st.download_button("Full snapshot (JSON)", json_report(center), "resq_snapshot.json", "application/json", use_container_width=True)
st.download_button("Incident register (CSV)", incidents_csv(center), "resq_incidents.csv", "text/csv", use_container_width=True)
st.download_button("Audit/event log (CSV)", event_log_csv(center), "resq_event_log.csv", "text/csv", use_container_width=True)
st.markdown("### Current incident register")
st.dataframe([{"ID":r.get("id"),"Type":r.get("disaster_type"),"Priority":r.get("priority_score"),"Urgency":r.get("urgency"),"Status":r.get("workflow_status") or r.get("status"),"People affected":r.get("people_affected"),"Medical":r.get("medical_emergency"),"Source":r.get("source")} for r in sorted(center.incidents,key=lambda x:int(x.get("priority_score") or 0),reverse=True)], use_container_width=True, hide_index=True)
st.caption("Do not share personal or sensitive incident data outside authorized response channels.")
