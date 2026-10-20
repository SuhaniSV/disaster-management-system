"""Shared Streamlit session helpers."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from core.llm_client import llm_configured
from core.persistence import is_configured, load_incidents, load_inventory
from core.state import CommandCenter


def get_center() -> CommandCenter:
    if "center" not in st.session_state:
        center = CommandCenter(
            bundle={
                "incidents": [],
                "resources": [],
                "hospitals": [],
                "shelters": [],
                "roads": [],
                "events": [],
            }
        )
        st.session_state.incident_store_configured = is_configured()
        st.session_state.incident_store_error = None

        if st.session_state.incident_store_configured:
            try:
                center.incidents = load_incidents()
                try:
                    inventory = load_inventory()
                    center.resources = inventory.get("resources", [])
                    center.hospitals = inventory.get("hospitals", [])
                    center.shelters = inventory.get("shelters", [])
                    st.session_state.inventory_store_error = None
                except Exception as inventory_exc:
                    # Incident persistence may already exist on older deployments.
                    # Inventory requires migrations/002_operational_inventory.sql.
                    st.session_state.inventory_store_error = (
                        f"Operational inventory tables are not ready ({type(inventory_exc).__name__}). "
                        "Run migrations/002_operational_inventory.sql in Supabase."
                    )
                center.recalculate(reason="Loaded saved incidents and available operational inventory")
            except Exception as exc:
                # Don't silently show an empty queue when the database could not load.
                st.session_state.incident_store_error = (
                    f"Saved incident reports could not be loaded ({type(exc).__name__}). "
                    "Check the DATABASE_URL secret and Supabase table migration."
                )
                st.error(st.session_state.incident_store_error)

        if llm_configured():
            center.ai_mode = "AI Mode: Active"
        st.session_state.center = center

    center: CommandCenter = st.session_state.center
    # Clear records loaded by earlier app versions from the session; they were sample CSV data.
    if getattr(center, "demo_mode", False):
        center = CommandCenter(
            bundle={
                "incidents": [],
                "resources": [],
                "hospitals": [],
                "shelters": [],
                "roads": [],
                "events": [],
            }
        )
        st.session_state.center = center
    if llm_configured() and center.ai_mode.startswith("Fallback"):
        center.ai_mode = "AI Mode: Active"
    elif not llm_configured() and str(center.ai_mode).startswith("AI Mode"):
        center.ai_mode = "Fallback Analysis Mode"
    return center


def persist(center: CommandCenter) -> None:
    st.session_state.center = center
