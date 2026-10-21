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
            "**If this app is deployed on Streamlit Community Cloud:** open the app's settings/manage page, "
            "find **Secrets**, add the keys shown below, save, then restart/reload the app. Local .env values "
            "on your computer are not automatically available to the deployed app.\n\n"
            "**IMD** — first obtain an API token from the official IMD API portal. The adapter requests the "
            "district nowcast and district warning endpoints; the token alone does not guarantee endpoint access.\n\n"
            "**NDMA SACHET / CAP** — use the official guide to obtain the authorized feed URL/identifier. "
            "Do not use a guessed URL. Never put credentials in GitHub or in the source code."
        )
        st.markdown(
            f"[IMD API portal]({IMD_API_PORTAL}) · [IMD API reference]({IMD_REFERENCE}) · "
            f"[SACHET portal]({NDMA_PORTAL}) · [SACHET CAP feed guide]({NDMA_FEED_GUIDE})"
        )
        st.code(
            'IMD_API_TOKEN = "YOUR_ISSUED_IMD_API_TOKEN"\n'
            'NDMA_CAP_FEED_URL = "YOUR_AUTHORIZED_SACHET_CAP_FEED_URL"',
            language="toml",
        )
        st.caption(
            "Replace both placeholders with values actually issued/provided by the official services. "
            "Do not paste secrets into chat, commit them, or use the example values literally."
        )

    with st.form("live_alert_filters"):
        col1, col2 = st.columns(2)
        state = col1.text_input("Filter IMD by state (optional)", placeholder="e.g. Maharashtra")
        district = col2.text_input("Filter IMD by district (optional)", placeholder="e.g. Pune")
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
    imd_public_alerts = imd.get("public_alerts", {}).get("alerts", [])
    ndma_rows = ndma.get("alerts", [])
    good_sources = int(bool(imd.get("ok"))) + int(bool(ndma.get("ok")))
    m1, m2, m3 = st.columns(3)
    m1.metric("Government alert items", len(imd_rows) + len(imd_public_alerts) + len(ndma_rows))
    m2.metric("Sources responding", f"{good_sources} / 2")
    successful_times = [x for x in (imd.get("fetched_at"), ndma.get("fetched_at")) if x]
    m3.metric("Last successful fetch", _fmt_time(max(successful_times) if successful_times else None))
    st.caption(
        "Requests are on-demand. IMD responses are cached for five minutes; SACHET uses ETag validation when provided. "
        "State/district filters apply to IMD records; the authorized SACHET feed is displayed as supplied by that feed."
    )

    with st.expander("Source status and diagnostics", expanded=True):
        st.markdown("**India Meteorological Department (IMD)**")
        st.markdown(f"Status: {'🟢 At least one request succeeded' if imd.get('ok') else '🟡 Unavailable'}")
        if not imd.get("configured"):
            st.warning(
                "IMD_API_TOKEN is missing. For the deployed app, add it in Streamlit Community Cloud → app settings → "
                "Secrets. For local runs, add it to your ignored .env file and restart Streamlit."
            )
        public_result = imd.get("public_alerts", {})
        if public_result.get("ok"):
            st.markdown(
                f"- **Public IMD CAP feed:** OK · {len(public_result.get('alerts', []))} alerts · "
                f"fetched {_fmt_time(public_result.get('fetched_at'))}"
            )
            st.caption(
                "This public CAP feed is linked from IMD's official Mausam website. "
                "It supplements the authenticated district API; it does not replace district nowcasts/warnings."
            )
        elif public_result.get("error"):
            st.caption(f"Public IMD CAP fallback: {public_result['error']}")
        for name in ("nowcast", "warnings"):
            result = imd.get(name, {})
            status = "OK" if result.get("ok") else "Unavailable"
            st.markdown(
                f"- **District {name}:** {status} · {len(result.get('rows', []))} records · "
                f"fetched {_fmt_time(result.get('fetched_at'))}"
            )
            if result.get("cached"):
                st.caption(f"{name.title()} response served from the five-minute cache.")
            if result.get("error"):
                st.caption(result["error"])
        st.markdown(f"[Open IMD API reference]({IMD_REFERENCE})")
        if public_result.get("source_url"):
            st.markdown(f"[Open public IMD CAP feed]({public_result['source_url']})")
        st.divider()
        st.markdown("**NDMA SACHET / India CAP**")
        st.markdown(f"Status: {'🟢 Request succeeded' if ndma.get('ok') else '🟡 Unavailable'}")
        if not ndma.get("configured"):
            st.warning(
                "NDMA_CAP_FEED_URL is missing. Obtain the authorized feed URL from the official SACHET guide, "
                "then add it under Streamlit Community Cloud Secrets or your local .env file."
            )
        if ndma.get("error"):
            st.caption(ndma["error"])
        st.caption(f"Records: {len(ndma_rows)} · fetched {_fmt_time(ndma.get('fetched_at'))}")
        if ndma.get("cached"):
            st.caption("SACHET returned HTTP 304; the previously fetched feed is being reused.")
        st.markdown(f"[Open SACHET portal]({NDMA_PORTAL}) · [CAP feed guide]({NDMA_FEED_GUIDE})")

    st.markdown("### IMD public CAP alerts")
    if not imd_public_alerts:
        st.info(
            "No public IMD CAP items were retrieved. District nowcasts and warnings still require the issued IMD API token."
        )
    else:
        for row in imd_public_alerts[:100]:
            with st.container(border=True):
                st.markdown(f"**{_value(row, ('title',), 'IMD weather alert')}**")
                st.caption(" · ".join(v for v in (_value(row, ("published",), ""), _value(row, ("source",), "IMD public CAP feed")) if v))
                if row.get("summary"):
                    st.write(row["summary"])
                if row.get("link", "").startswith("https://"):
                    st.markdown(f"[Verify alert at source]({row['link']})")

    st.markdown("### IMD district nowcasts")
    if not imd.get("nowcast", {}).get("ok"):
        st.info("Nowcast data is unavailable. See the IMD status and diagnostic message above.")
    elif not imd.get("nowcast", {}).get("rows"):
        st.info("The request succeeded, but no nowcast records matched these filters. This does not establish that no warnings exist.")
    else:
        for row in imd["nowcast"]["rows"][:50]:
            title = _value(row, ("District", "district", "district_name", "Station", "station", "name"), "District nowcast")
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(row)

    st.markdown("### IMD district warnings")
    if not imd.get("warnings", {}).get("ok"):
        st.info("Warning data is unavailable. See the IMD status and diagnostic message above.")
    elif not imd.get("warnings", {}).get("rows"):
        st.info("The request succeeded, but no warning records matched these filters. This does not establish that no warnings exist.")
    else:
        for row in imd["warnings"]["rows"][:50]:
            title = _value(row, ("District", "district", "district_name", "warning", "Warning", "event"), "District warning")
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(row)

    st.markdown("### NDMA SACHET / CAP alerts")
    if not ndma.get("configured"):
        st.info("Feed setup is required. Use the official SACHET guide to obtain the authorized feed URL.")
    elif not ndma.get("ok"):
        st.info(ndma.get("error") or "Feed unavailable. Check the official source and feed access.")
    elif not ndma_rows:
        st.info("The feed request succeeded but returned no parseable alert items. Check the feed format and source response.")
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
