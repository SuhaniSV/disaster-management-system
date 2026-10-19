"""UI for read-only official government hazard feeds."""
from __future__ import annotations

from datetime import datetime
import streamlit as st

from core.live_data import (
    IMD_API_PORTAL, IMD_REFERENCE, NDMA_FEED_GUIDE, NDMA_PORTAL,
    get_imd_live_data, get_ndma_cap_alerts,
)


def _fmt_time(value: str | None) -> str:
    if not value:
        return "Not fetched"
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime("%d %b %Y, %H:%M:%S %Z")
    except (ValueError, TypeError):
        return value


def _value(row: dict, keys: tuple[str, ...], fallback: str = "—") -> str:
    for key in keys:
        if row.get(key) not in (None, ""):
            return str(row[key])
    return fallback


def render_live_alerts() -> None:
    st.markdown('<div class="resq-kicker">RESQ-AI / OFFICIAL SOURCES</div>', unsafe_allow_html=True)
    st.title("Live Government Alerts")
    st.caption("Current IMD weather warnings and NDMA SACHET/CAP alerts, with feed health and source traceability.")
    st.warning(
        "A weather warning is a hazard signal, not a verified rescue incident. These feeds never create incidents, "
        "change deterministic priority scores, or dispatch resources automatically.",
        icon="⚠️",
    )

    with st.expander("Connect official feeds", expanded=False):
        st.markdown(
            "**IMD** — obtain API access from the official portal and set IMD_API_TOKEN in .env or Streamlit secrets. "
            "The adapter reads district nowcast and district warning endpoints documented by IMD.\n\n"
            "**NDMA SACHET / CAP** — set NDMA_CAP_FEED_URL to a feed URL supplied by SACHET/your authorized agency. "
            "No undocumented feed identifier is guessed.\n\n"
            "Use the links below to confirm current access requirements. Never put credentials in source code."
        )
        st.markdown(
            f"[IMD API portal]({IMD_API_PORTAL}) · [IMD API reference]({IMD_REFERENCE}) · "
            f"[SACHET portal]({NDMA_PORTAL}) · [SACHET CAP feed guide]({NDMA_FEED_GUIDE})"
        )
        st.code(
            "IMD_API_TOKEN=your-issued-token\n"
            "NDMA_CAP_FEED_URL=https://sachet.ndma.gov.in/your-authorized-feed-url",
            language="text",
        )

    with st.form("live_alert_filters"):
        col1, col2 = st.columns(2)
        state = col1.text_input("Filter by state (optional)", placeholder="e.g. Maharashtra")
        district = col2.text_input("Filter by district (optional)", placeholder="e.g. Pune")
        refresh = st.form_submit_button("Fetch latest government data", type="primary")

    desired_filters = {"state": state.strip(), "district": district.strip()}
    if "resq_live_data" not in st.session_state or refresh or st.session_state.get("resq_live_data", {}).get("filters") != desired_filters:
        with st.spinner("Requesting official government feeds…"):
            st.session_state["resq_live_data"] = {
                "imd": get_imd_live_data(state=state.strip(), district=district.strip()),
                "ndma": get_ndma_cap_alerts(),
                "filters": desired_filters,
            }
    data = st.session_state["resq_live_data"]
    imd, ndma = data["imd"], data["ndma"]

    imd_rows = imd.get("nowcast", {}).get("rows", []) + imd.get("warnings", {}).get("rows", [])
    ndma_rows = ndma.get("alerts", [])
    good_sources = int(bool(imd.get("ok"))) + int(bool(ndma.get("ok")))
    m1, m2, m3 = st.columns(3)
    m1.metric("Government alert items", len(imd_rows) + len(ndma_rows))
    m2.metric("Sources responding", f"{good_sources} / 2")
    m3.metric("Last successful fetch", _fmt_time(max([x for x in (imd.get("fetched_at"), ndma.get("fetched_at")) if x] or [None])))
    st.caption("Requests are on-demand. IMD responses are cached for five minutes; SACHET uses ETag validation when provided.")

    with st.expander("Source status and diagnostics", expanded=True):
        st.markdown("**India Meteorological Department (IMD)**")
        st.markdown(f"Status: {'🟢 Request succeeded' if imd.get('ok') else '🟡 Not connected / unavailable'}")
        if not imd.get("configured"):
            st.info("IMD API token is not configured. Add IMD_API_TOKEN locally and refresh.")
        for name in ("nowcast", "warnings"):
            result = imd.get(name, {})
            st.markdown(f"- **District {name}:** {'OK' if result.get('ok') else 'Unavailable'} · {len(result.get('rows', []))} records · fetched {_fmt_time(result.get('fetched_at'))}")
            if result.get("error"):
                st.caption(result["error"])
        st.markdown(f"[Open IMD source]({IMD_REFERENCE})")
        st.divider()
        st.markdown("**NDMA SACHET / India CAP**")
        st.markdown(f"Status: {'🟢 Request succeeded' if ndma.get('ok') else '🟡 Not connected / unavailable'}")
        st.caption(ndma.get("error") or "")
        st.caption(f"Records: {len(ndma_rows)} · fetched {_fmt_time(ndma.get('fetched_at'))}")
        st.markdown(f"[Open SACHET portal]({NDMA_PORTAL}) · [CAP feed guide]({NDMA_FEED_GUIDE})")

    st.markdown("### IMD district nowcasts")
    if not imd.get("nowcast", {}).get("ok"):
        st.info("Nowcast data is unavailable. Confirm IMD API access and token before interpreting the absence of records.")
    elif not imd.get("nowcast", {}).get("rows"):
        st.info("The successful response returned no records matching these filters.")
    else:
        for row in imd["nowcast"]["rows"][:50]:
            title = _value(row, ("District", "district", "district_name", "Station", "station", "name"), "District nowcast")
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(row)

    st.markdown("### IMD district warnings")
    if not imd.get("warnings", {}).get("ok"):
        st.info("Warning data is unavailable. See source diagnostics above.")
    elif not imd.get("warnings", {}).get("rows"):
        st.info("The successful response returned no warning records matching these filters.")
    else:
        for row in imd["warnings"]["rows"][:50]:
            title = _value(row, ("District", "district", "district_name", "warning", "Warning", "event"), "District warning")
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(row)

    st.markdown("### NDMA SACHET / CAP alerts")
    if not ndma.get("configured"):
        st.info("NDMA feed setup is required. Use the official SACHET guide to obtain the authorized feed URL.")
    elif not ndma.get("ok"):
        st.info(ndma.get("error") or "Feed unavailable. Check the official source.")
    elif not ndma_rows:
        st.info("The feed request succeeded but returned no parseable alert items.")
    else:
        for row in ndma_rows[:100]:
            with st.container(border=True):
                st.markdown(f"**{_value(row, ('title',), 'Government alert')}**")
                st.caption(" · ".join(v for v in (_value(row, ("published",), ""), _value(row, ("source",), "")) if v))
                if row.get("summary"):
                    st.write(row["summary"])
                if row.get("link", "").startswith("https://"):
                    st.markdown(f"[Verify alert at source]({row['link']})")

    st.caption(
        "Live-source integration is best-effort and depends on official API permissions, availability, and payload formats. "
        "Always verify an alert's location, issue/expiry time and on-the-ground impact with authorities."
    )
