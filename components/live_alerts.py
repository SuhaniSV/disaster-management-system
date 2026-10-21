
"""UI for read-only official government hazard feeds."""
from __future__ import annotations

from datetime import datetime
import time

import streamlit as st

from core.alert_translation import english_record, english_text
from core.gdacs_data import get_gdacs_events
from core.live_data import (
    IMD_API_PORTAL,
    IMD_REFERENCE,
    NDMA_FEED_GUIDE,
    NDMA_PORTAL,
    get_imd_live_data,
    get_imd_public_warning_outlook,
    get_ndma_cap_alerts,
    get_usgs_india_earthquakes,
)


def _fmt_time(value: str | None) -> str:
    """Format a source timestamp for display."""
    if not value:
        return "Not fetched"

    try:
        return (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            .astimezone()
            .strftime("%d %b %Y, %H:%M:%S %Z")
        )
    except (ValueError, TypeError):
        return value


def _value(
    row: dict,
    keys: tuple[str, ...],
    fallback: str = "—",
) -> str:
    """Return the first non-empty, English-readable value."""
    for key in keys:
        value = row.get(key)

        if value in (None, ""):
            continue

        translated = english_text(str(value))
        if translated and translated.strip():
            return translated.strip()

    return fallback


def _matches_area(row: dict, *queries: str) -> bool:
    """Match every supplied search term against source-provided fields."""
    required = [
        query.strip().casefold()
        for query in queries
        if query and query.strip()
    ]

    if not required:
        return True

    translated = english_record(row)
    terms: list[str] = []

    excluded_keys = {
        "link",
        "url",
        "source_url",
        "guid",
        "identifier",
        "id",
    }

    def collect(value) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key).casefold() not in excluded_keys:
                    terms.append(str(key))
                    collect(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                collect(item)
        elif isinstance(value, str):
            terms.append(value)
        elif isinstance(value, (int, float)):
            terms.append(str(value))

    collect(translated)
    searchable = " ".join(terms).casefold()

    return all(query in searchable for query in required)


def _has_filters(state: str, district: str, area_query: str) -> bool:
    """Return whether any user-entered area filter is active."""
    return any(
        value.strip()
        for value in (state, district, area_query)
    )


def _render_alert(
    row: dict,
    *,
    title_keys: tuple[str, ...] = ("title",),
    default_title: str = "",
    show_summary: bool = True,
) -> bool:
    """Render a source-backed alert. Return False if its title is unreadable."""
    title = _value(row, title_keys, default_title)

    if not title or title == "—":
        return False

    with st.container(border=True):
        st.markdown(f"**{title}**")

        metadata = [
            _value(row, ("published",), ""),
            _value(row, ("source",), ""),
        ]
        metadata = [item for item in metadata if item and item != "—"]

        if metadata:
            st.caption(" · ".join(metadata))

        summary = english_text(str(row.get("summary", "")))
        if show_summary and summary and summary.strip():
            st.write(summary)

        link = row.get("link", "")
        if isinstance(link, str) and link.startswith("https://"):
            st.markdown(f"[Verify alert at source]({link})")

    return True


@st.fragment(run_every=300)
def render_live_alerts() -> None:
    """Display read-only alerts from official government feeds."""
    st.markdown(
        '<div class="resq-kicker">RESQ-AI / OFFICIAL SOURCES</div>',
        unsafe_allow_html=True,
    )
    st.title("Live Government Alerts")
    st.caption(
        "Current IMD weather warnings and NDMA SACHET/CAP alerts, "
        "with feed health and source traceability."
    )

    st.warning(
        "A weather warning is a hazard signal, not a verified rescue incident. "
        "These feeds never create incidents, change deterministic priority "
        "scores, or dispatch resources automatically.",
        icon="⚠️",
    )

    with st.expander("Connect official feeds", expanded=False):
        st.markdown(
            "**If this app is deployed on Streamlit Community Cloud:** "
            "open the app's settings/manage page, find **Secrets**, add "
            "the required keys, save, and restart or reload the app. "
            "Local `.env` values on your computer are not automatically "
            "available to the deployed app.\n\n"
            "**IMD** — first obtain an API token from the official IMD API "
            "portal. The adapter requests district nowcast and district "
            "warning endpoints; a token alone does not guarantee endpoint "
            "access.\n\n"
            "**NDMA SACHET / CAP** — the official integration guide documents "
            "the CAP XML endpoint. Add either an authorized feed URL or the "
            "identifier issued by SACHET. The identifier is not public or "
            "guessable; do not invent one. This integrated CAP channel may "
            "carry alerts from IMD, CWC, INCOIS, DGRE, GSI and FSI, depending "
            "on the identifier and what each agency publishes. Never put "
            "credentials in GitHub or source code."
        )

        st.markdown(
            f"[IMD API portal]({IMD_API_PORTAL}) · "
            f"[IMD API reference]({IMD_REFERENCE}) · "
            f"[SACHET portal]({NDMA_PORTAL}) · "
            f"[SACHET CAP feed guide]({NDMA_FEED_GUIDE})"
        )

        st.code(
            'IMD_API_TOKEN = "YOUR_ISSUED_IMD_API_TOKEN"\n'
            'NDMA_CAP_FEED_URL = ""\n'
            'NDMA_CAP_IDENTIFIER = "YOUR_SACHET_ISSUED_IDENTIFIER"',
            language="toml",
        )

        st.caption(
            "Replace the placeholders only with values issued or provided "
            "by the official services. Do not paste secrets into chat, "
            "commit them, or use the example values literally."
        )

    with st.form("live_alert_filters"):
        col1, col2 = st.columns(2)

        state = col1.text_input(
            "Filter all alerts by state (optional)",
            placeholder="e.g. Uttar Pradesh",
        )
        district = col2.text_input(
            "Filter all alerts by district (optional)",
            placeholder="e.g. Gautam Buddha Nagar",
        )

        refresh = st.form_submit_button(
            "Fetch latest government data",
            type="primary",
        )

    area_query = st.text_input(
        "Search alerts by area",
        placeholder="Enter a city, district, or state — e.g. Noida, Pune, Kerala",
        help=(
            "Filters displayed alerts across feeds using location and alert "
            "text supplied by the source. It does not guess missing locations."
        ),
    )

    state = state.strip()
    district = district.strip()
    area_query = area_query.strip()

    desired_filters = {
        "state": state,
        "district": district,
    }

    cached_data = st.session_state.get("resq_live_data", {})
    fetched_at = st.session_state.get(
        "resq_live_data_fetched_monotonic",
        0,
    )

    should_fetch = (
        not cached_data
        or refresh
        or cached_data.get("filters") != desired_filters
        or "usgs" not in cached_data
        or "gdacs" not in cached_data
        or "imd_outlook" not in cached_data
        or time.monotonic() - fetched_at >= 300
    )

    if should_fetch:
        with st.spinner("Requesting official government feeds…"):
            try:
                imd = get_imd_live_data(
                    state=state,
                    district=district,
                )
            except Exception as exc:
                imd = {
                    "ok": False,
                    "configured": False,
                    "error": f"IMD request failed: {type(exc).__name__}",
                    "nowcast": {"ok": False, "rows": []},
                    "warnings": {"ok": False, "rows": []},
                    "public_alerts": {
                        "ok": False,
                        "alerts": [],
                        "error": "Public IMD feed request failed.",
                    },
                }

            try:
                imd_outlook = get_imd_public_warning_outlook()
            except Exception as exc:
                imd_outlook = {
                    "ok": False,
                    "rows": [],
                    "error": f"IMD public warning outlook failed: {type(exc).__name__}",
                    "fetched_at": None,
                    "source_url": "https://mausam.imd.gov.in/imd_latest/contents/subdivisionwise-warning_mc.php?id=25",
                }

            try:
                ndma = get_ndma_cap_alerts()
            except Exception as exc:
                ndma = {
                    "ok": False,
                    "configured": False,
                    "error": f"NDMA request failed: {type(exc).__name__}",
                    "alerts": [],
                }

            try:
                usgs = get_usgs_india_earthquakes()
            except Exception as exc:
                usgs = {
                    "ok": False,
                    "events": [],
                    "error": f"USGS request failed: {type(exc).__name__}",
                    "fetched_at": None,
                    "records_seen": 0,
                }

            try:
                gdacs = get_gdacs_events()
            except Exception as exc:
                gdacs = {
                    "ok": False,
                    "events": [],
                    "error": f"GDACS request failed: {type(exc).__name__}",
                    "fetched_at": None,
                    "records_seen": 0,
                    "source_url": "https://www.gdacs.org/",
                }

            st.session_state["resq_live_data"] = {
                "imd": imd,
                "ndma": ndma,
                "usgs": usgs,
                "gdacs": gdacs,
                "imd_outlook": imd_outlook,
                "filters": desired_filters,
            }
            st.session_state["resq_live_data_fetched_monotonic"] = (
                time.monotonic()
            )

    data = st.session_state["resq_live_data"]
    imd = data.get("imd", {})
    ndma = data.get("ndma", {})
    usgs = data.get("usgs", {})
    gdacs = data.get("gdacs", {"ok": False, "events": []})
    imd_outlook = data.get("imd_outlook", {"ok": False, "rows": []})

    nowcast_result = imd.get("nowcast", {})
    warning_result = imd.get("warnings", {})
    public_result = imd.get("public_alerts", {})

    nowcast_rows = nowcast_result.get("rows", [])
    warning_rows = warning_result.get("rows", [])
    imd_public_alerts = public_result.get("alerts", [])
    ndma_rows = ndma.get("alerts", [])

    good_sources = (
        int(bool(imd.get("ok")))
        + int(bool(ndma.get("ok")))
        + int(bool(usgs.get("ok")))
    )

    successful_times = [
        value
        for value in (
            imd.get("fetched_at"),
            ndma.get("fetched_at"),
            usgs.get("fetched_at"),
            gdacs.get("fetched_at"),
        )
        if value
    ]

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Live alert / event items",
        len(nowcast_rows)
        + len(warning_rows)
        + len(imd_public_alerts)
        + len(ndma_rows)
        + len(usgs.get("events", []))
        + len(gdacs.get("events", [])),
    )
    good_sources += int(bool(gdacs.get("ok")))
    m2.metric("Sources responding", f"{good_sources} / 4")
    m3.metric(
        "Last successful fetch",
        _fmt_time(max(successful_times) if successful_times else None),
    )

    st.caption(
        "Feeds are rechecked every five minutes while this page remains "
        "open. IMD responses use a five-minute cache; SACHET uses ETag "
        "validation when provided. State, district, and area filters apply "
        "to displayed source records. IMD state and district inputs also "
        "constrain IMD API requests. Records whose titles cannot be "
        "translated are omitted rather than displayed with placeholders. "
        "Original source links remain available."
    )

    with st.expander("Source status and diagnostics", expanded=True):
        st.markdown("**India Meteorological Department (IMD)**")
        st.markdown(
            "Status: "
            + (
                "🟢 Public feed reachable"
                if public_result.get("ok")
                else "🟡 Public feed unavailable"
            )
        )

        if public_result.get("ok"):
            st.caption(
                f"Active alerts: {len(imd_public_alerts)} · "
                f"CAP records: {public_result.get('records_seen', 0)} · "
                f"Regional outlook warnings: "
                f"{len(imd_outlook.get('rows', []))} · "
                f"Fetched {_fmt_time(public_result.get('fetched_at'))}"
            )
        elif public_result.get("error"):
            st.caption(f"Public feed error: {public_result['error']}")

        if not imd.get("configured"):
            st.caption(
                "District nowcast and warnings: Unavailable — "
                "`IMD_API_TOKEN` not configured."
            )
        else:
            st.caption(
                f"District nowcast: "
                f"{'Available' if nowcast_result.get('ok') else 'Unavailable'} "
                f"({len(nowcast_rows)} records) · "
                f"District warnings: "
                f"{'Available' if warning_result.get('ok') else 'Unavailable'} "
                f"({len(warning_rows)} records)"
            )

        st.markdown(
            f"[Open IMD API reference]({IMD_REFERENCE}) · "
            f"[Open IMD CAP feed]({public_result.get('source_url') or 'https://wis2box.imd.gov.in/oapi/collections/messages/items'})"
        )

        st.divider()
        st.markdown("**NDMA SACHET / India CAP**")
        st.markdown(
            "Status: "
            + (
                "🟢 Request succeeded"
                if ndma.get("ok")
                else "🟡 Unavailable"
            )
        )

        if not ndma.get("configured"):
            st.warning(
                "NDMA_CAP_FEED_URL is missing. Obtain the authorized feed "
                "URL from the official SACHET guide, then add it under "
                "Streamlit Community Cloud Secrets or your local `.env` file."
            )

        if ndma.get("error"):
            st.caption(str(ndma["error"]))

        st.caption(
            f"Records: {len(ndma_rows)} · "
            f"fetched {_fmt_time(ndma.get('fetched_at'))}"
        )

        if ndma.get("cached"):
            st.caption(
                "SACHET returned HTTP 304; the previously fetched feed is reused."
            )

        st.markdown(
            f"[Open SACHET portal]({NDMA_PORTAL}) · "
            f"[CAP feed guide]({NDMA_FEED_GUIDE})"
        )

        st.divider()
        st.markdown("**USGS earthquake feed — India region**")
        st.markdown(
            "Status: "
            + ("🟢 Request succeeded" if usgs.get("ok") else "🟡 Unavailable")
        )
        st.caption(
            f"India-region events: {len(usgs.get('events', []))} · "
            f"USGS records checked: {usgs.get('records_seen', 0)} · "
            f"fetched {_fmt_time(usgs.get('fetched_at'))}"
        )
        if usgs.get("error"):
            st.caption(str(usgs["error"]))
        st.markdown(f"[Open USGS earthquake feed]({usgs.get('source_url', 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson')})")

        st.divider()
        st.markdown("**GDACS global disaster feed**")
        st.markdown(
            "Status: "
            + ("🟢 Request succeeded" if gdacs.get("ok") else "🟡 Unavailable")
        )
        st.caption(
            f"Events returned: {len(gdacs.get('events', []))} · "
            f"Records checked: {gdacs.get('records_seen', 0)} · "
            f"Fetched {_fmt_time(gdacs.get('fetched_at'))}"
        )
        if gdacs.get("error"):
            st.caption(str(gdacs["error"]))
        st.markdown(f"[Open official GDACS feed]({gdacs.get('source_url', 'https://www.gdacs.org/')})")

    any_filter = _has_filters(state, district, area_query)

    # Public IMD CAP alerts
    st.markdown("### IMD public CAP alerts")

    if not imd_public_alerts:
        checked = public_result.get("records_seen", 0)

        if checked:
            st.info(
                f"The official IMD feed was checked ({checked} CAP records), "
                "but no active alerts were returned. District nowcasts and "
                "warnings still require the issued IMD API token."
            )
        elif public_result.get("error"):
            st.info(
                "Public IMD CAP alerts are currently unavailable. "
                "Check the source diagnostics above."
            )
        else:
            st.info(
                "No active public IMD CAP items were retrieved. ResQ-AI "
                "checks the public RSS feed and the official IMD WIS2 CAP "
                "catalogue when available. District nowcasts and warnings "
                "still require the issued IMD API token."
            )
    else:
        matched = [
            row
            for row in imd_public_alerts
            if _matches_area(row, state, district, area_query)
        ]

        shown = 0

        for row in matched[:100]:
            if _render_alert(
                row,
                title_keys=("title", "headline", "event"),
                default_title="",
            ):
                shown += 1

        if any_filter and shown == 0:
            st.info(
                "No English-readable public IMD alerts matched these filters. "
                "Try a broader state, district, or city name."
            )

    # Current public IMD subdivision outlook (separate from CAP events)
    st.markdown("### IMD public warning outlook")
    st.caption(
        "Official public forecast warnings from IMD RMC New Delhi. "
        "This is a regional 7-day outlook, not a CAP incident feed."
    )
    if not imd_outlook.get("ok"):
        st.info(
            "The public IMD subdivision outlook could not be retrieved. "
            "Use the official source link below to verify current warnings."
        )
    else:
        outlook_rows = imd_outlook.get("rows", [])
        if not outlook_rows:
            st.success(
                "The fetched IMD regional outlook contains no non-No-warning "
                "entries for the displayed forecast days."
            )
        else:
            st.caption(
                f"{len(outlook_rows)} official forecast warning entries · "
                f"issued {_fmt_time(imd_outlook.get('fetched_at'))}"
            )
            for row in outlook_rows[:50]:
                _render_alert(
                    row,
                    title_keys=("title",),
                    default_title="IMD forecast warning",
                )
    outlook_url = imd_outlook.get("source_url")
    if isinstance(outlook_url, str) and outlook_url.startswith("https://"):
        st.markdown(f"[Open current IMD public warning outlook]({outlook_url})")

    # IMD district nowcasts
    st.markdown("### IMD district nowcasts")

    if not nowcast_result.get("ok"):
        st.info(
            "Nowcast data is unavailable. See the IMD status and diagnostic "
            "message above."
        )
    elif not nowcast_rows:
        st.info(
            "The request succeeded, but no nowcast records were returned "
            "for these API filters. This does not establish that no warnings exist."
        )
    else:
        shown = 0

        for row in nowcast_rows:
            if not _matches_area(row, state, district, area_query):
                continue

            title = _value(
                row,
                (
                    "District",
                    "district",
                    "district_name",
                    "Station",
                    "station",
                    "name",
                ),
                "",
            )

            rendered = english_record(row)
            has_readable_data = isinstance(rendered, dict) and any(
                value not in (None, "")
                for value in rendered.values()
            )

            if not title or title == "—" or not has_readable_data:
                continue

            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(rendered)

            shown += 1
            if shown >= 50:
                break

        if any_filter and shown == 0:
            st.info(
                "No English-readable nowcast records matched these filters. "
                "Try a broader state, district, or city name."
            )

    # IMD district warnings
    st.markdown("### IMD district warnings")

    if not warning_result.get("ok"):
        st.info(
            "Warning data is unavailable. See the IMD status and diagnostic "
            "message above."
        )
    elif not warning_rows:
        st.info(
            "The request succeeded, but no warning records were returned "
            "for these API filters. This does not establish that no warnings exist."
        )
    else:
        shown = 0

        for row in warning_rows:
            # Apply all three filters consistently.
            if not _matches_area(row, state, district, area_query):
                continue

            title = _value(
                row,
                (
                    "District",
                    "district",
                    "district_name",
                    "warning",
                    "Warning",
                    "event",
                    "title",
                    "headline",
                ),
                "",
            )

            rendered = english_record(row)

            if not title or title == "—":
                continue

            with st.container(border=True):
                st.markdown(f"**{title}**")
                if isinstance(rendered, dict):
                    st.write(rendered)
                else:
                    st.write(rendered)

                link = row.get("link", "")
                if isinstance(link, str) and link.startswith("https://"):
                    st.markdown(f"[Verify alert at source]({link})")

            shown += 1
            if shown >= 50:
                break

        if any_filter and shown == 0:
            st.info(
                "No English-readable district warnings matched these filters. "
                "Try a broader state, district, or city name."
            )

    # Official global multi-hazard events from GDACS
    st.markdown("### Global disaster alerts — GDACS")
    st.caption(
        "Official global event feed covering earthquakes, floods, tropical "
        "cyclones, volcanoes, droughts and wildfires. These are hazard alerts, "
        "not verified local rescue incidents."
    )
    gdacs_events = [
        row for row in gdacs.get("events", [])
        if _matches_area(row, state, district, area_query)
    ]
    if not gdacs.get("ok"):
        st.info(
            gdacs.get("error")
            or "The official GDACS feed is unavailable; check source status above."
        )
    elif not gdacs_events:
        st.info(
            "No recent GDACS events matched the current filters. This is not "
            "a guarantee that no local hazards exist."
        )
    else:
        for row in gdacs_events[:50]:
            _render_alert(
                row,
                title_keys=("title",),
                default_title="GDACS disaster event",
            )

    # Recent earthquakes within the India-region bounding box
    st.markdown("### Recent earthquakes — India region")
    earthquake_events = [
        row for row in usgs.get("events", [])
        if _matches_area(row, state, district, area_query)
    ]
    if not usgs.get("ok"):
        st.info(usgs.get("error") or "USGS earthquake data is unavailable.")
    elif not earthquake_events:
        st.info(
            "No events from the USGS past-day feed matched the India-region "
            "bounds and current filters. This does not mean all Indian seismic "
            "activity has been ruled out."
        )
    else:
        for row in earthquake_events[:50]:
            with st.container(border=True):
                st.markdown(f"**{row.get('title', 'Earthquake event')}**")
                st.caption(
                    f"{row.get('published') or 'Time not supplied'} · "
                    f"{row.get('source', 'USGS')}"
                )
                st.write(row.get("summary", ""))
                if row.get("link", "").startswith("https://"):
                    st.markdown(f"[Verify event at USGS]({row['link']})")

    # NDMA SACHET / CAP alerts
    st.markdown("### NDMA SACHET / CAP alerts")

    if not ndma.get("configured"):
        st.info(
            "Feed setup is required. Use the official SACHET guide to obtain "
            "the authorized feed URL."
        )
    elif not ndma.get("ok"):
        st.info(
            ndma.get("error")
            or "The feed is unavailable. Check the official source and feed access."
        )
    elif not ndma_rows:
        st.info(
            "The feed request succeeded but returned no parseable alert items. "
            "Check the feed format and source response."
        )
    else:
        matched = [
            row
            for row in ndma_rows
            if _matches_area(row, state, district, area_query)
        ]

        shown = 0

        for row in matched[:100]:
            if _render_alert(
                row,
                title_keys=("title", "headline", "event"),
                default_title="",
            ):
                shown += 1

        if any_filter and shown == 0:
            st.info(
                "No English-readable NDMA alerts matched these filters. "
                "Try a broader state, district, or city name."
            )

    st.caption(
        "Live-source integration is best-effort and depends on official API "
        "permissions, availability, and payload formats. Always verify an "
        "alert's location, issue and expiry times, and on-the-ground impact "
        "with the relevant authorities."
    )