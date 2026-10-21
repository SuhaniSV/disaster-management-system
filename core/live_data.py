
"""Official live-data adapters for IMD weather warnings and NDMA CAP alerts.

These read-only feeds remain separate from operator-reported incidents and never
change deterministic incident scores or dispatch resources.
"""
from __future__ import annotations

import base64
import hashlib
import os
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote, urlparse

import certifi
import requests


IMD_API_BASE = os.getenv(
    "IMD_API_BASE",
    "https://api.imd.gov.in/api/v1",
).rstrip("/")

IMD_API_PORTAL = "https://api.imd.gov.in/public/index.php"
IMD_REFERENCE = "https://api.imd.gov.in/public/api_reference.html"

# Public IMD CAP/RSS feed linked from the official Mausam website.
IMD_PUBLIC_CAP_URL = (
    "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml"
)

# Official IMD WIS2 CAP catalogue used when RSS has no active alerts.
IMD_WIS2_CAP_URL = (
    "https://wis2box.imd.gov.in/oapi/collections/messages/items"
)
IMD_CAP_METADATA_ID = "urn:wmo:md:in-imd:cap_alerts"

NDMA_PORTAL = "https://sachet.ndma.gov.in/"
NDMA_FEED_GUIDE = "https://sachet.ndma.gov.in/CapFeed"

_TIMEOUT_SECONDS = 12
_CACHE_SECONDS = 300

_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] = {}


def _now() -> str:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _setting(name: str, default: str = "") -> str:
    """Read environment variables first, then Streamlit secrets."""
    value = os.getenv(name, "").strip()
    if value:
        return value

    try:
        import streamlit as st

        secret = st.secrets.get(name, default)
        return str(secret).strip() if secret else default
    except Exception:
        return default


def _as_rows(payload: Any) -> list[dict[str, Any]]:
    """Normalize lists and common wrapped JSON response shapes."""
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]

    if isinstance(payload, dict):
        for key in ("data", "items", "results", "records"):
            value = payload.get(key)

            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]

            if isinstance(value, dict):
                for nested in ("items", "records", "observed", "alerts"):
                    nested_value = value.get(nested)
                    if isinstance(nested_value, list):
                        return [
                            row
                            for row in nested_value
                            if isinstance(row, dict)
                        ]

        return [payload] if payload else []

    return []


def _cached_get_json(url: str, token: str) -> dict[str, Any]:
    """Fetch authenticated IMD JSON with a five-minute credential-scoped cache."""
    if not token:
        return {
            "ok": False,
            "rows": [],
            "fetched_at": None,
            "cached": False,
            "error": (
                "IMD_API_TOKEN is missing. Obtain an issued token from the "
                "official IMD API portal and configure it in app secrets."
            ),
        }

    # Never store the token itself in the cache key.
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    cache_key = f"imd-api:{url}:{token_hash}"
    now = time.monotonic()

    with _lock:
        cached = _cache.get(cache_key)

        if cached and now - cached["stored_at"] < _CACHE_SECONDS:
            return {
                "ok": True,
                "rows": cached["rows"],
                "fetched_at": cached["fetched_at"],
                "cached": True,
                "error": None,
            }

    header_name = (
        _setting("IMD_API_AUTH_HEADER", "Authorization").strip()
        or "Authorization"
    )
    scheme = _setting("IMD_API_AUTH_SCHEME", "Bearer").strip()
    auth_value = f"{scheme} {token}".strip()

    headers = {
        header_name: auth_value,
        "Accept": "application/json",
        "User-Agent": "ResQ-AI/1.0 (government-data dashboard)",
    }

    if cached and cached.get("etag"):
        headers["If-None-Match"] = cached["etag"]

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=_TIMEOUT_SECONDS,
            verify=certifi.where(),
        )

        if response.status_code == 304 and cached:
            with _lock:
                cached["stored_at"] = now

            return {
                "ok": True,
                "rows": cached["rows"],
                "fetched_at": cached["fetched_at"],
                "cached": True,
                "error": None,
            }

        response.raise_for_status()
        payload = response.json()
        rows = _as_rows(payload)
        fetched_at = _now()

        with _lock:
            _cache[cache_key] = {
                "rows": rows,
                "fetched_at": fetched_at,
                "stored_at": now,
                "etag": response.headers.get("ETag"),
            }

        return {
            "ok": True,
            "rows": rows,
            "fetched_at": fetched_at,
            "cached": False,
            "error": None,
        }

    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", "unknown")

        if status in (401, 403):
            message = (
                f"IMD rejected the credentials (HTTP {status}). Check the "
                "issued token, permissions, and documented authentication header."
            )
        else:
            message = (
                f"IMD request failed (HTTP {status}). Check endpoint access "
                "and the current IMD API reference."
            )

    except (requests.RequestException, ValueError) as exc:
        message = (
            f"Could not retrieve valid IMD data: {type(exc).__name__}. "
            "Check network access and the official API response format."
        )

    return {
        "ok": False,
        "rows": [],
        "fetched_at": None,
        "cached": False,
        "error": message,
    }


def _matches(
    row: dict[str, Any],
    state: str = "",
    district: str = "",
) -> bool:
    """Match source-provided state and district fields."""
    state_keys = ("State", "STATE", "state", "state_name")
    district_keys = (
        "District",
        "DISTRICT",
        "district",
        "district_name",
        "Station",
        "station",
    )

    state_text = " ".join(
        str(row.get(key, "")) for key in state_keys
    ).casefold()

    district_text = " ".join(
        str(row.get(key, "")) for key in district_keys
    ).casefold()

    state_query = state.strip().casefold()
    district_query = district.strip().casefold()

    return (
        (not state_query or state_query in state_text)
        and (
            not district_query
            or district_query in district_text
        )
    )


def _clean_rows(
    rows: list[dict[str, Any]],
    state: str = "",
    district: str = "",
) -> list[dict[str, Any]]:
    """Filter district API records without inventing location data."""
    return [
        row
        for row in rows
        if _matches(row, state, district)
    ]


def _xml_text(element: ET.Element, local_name: str) -> str:
    """Read the first matching XML element by its local tag name."""
    for child in element.iter():
        tag = child.tag.split("}")[-1].lower()

        if tag == local_name.lower() and child.text:
            return child.text.strip()

    return ""


def _parse_cap_xml(
    content: bytes,
    source: str = "NDMA SACHET CAP feed",
) -> list[dict[str, Any]]:
    """Parse RSS item XML or a single CAP alert XML document."""
    try:
        root = ET.fromstring(content)
    except (ET.ParseError, ValueError, TypeError):
        return []

    items: list[dict[str, Any]] = []

    rss_items = [
        node
        for node in root.iter()
        if node.tag.split("}")[-1].lower() == "item"
    ]

    for node in rss_items:
        item = {
            "title": _xml_text(node, "title"),
            "summary": _xml_text(node, "description"),
            "link": _xml_text(node, "link"),
            "published": (
                _xml_text(node, "pubDate")
                or _xml_text(node, "sent")
            ),
            "expires": _xml_text(node, "expires"),
            "severity": _xml_text(node, "severity"),
            "area": _xml_text(node, "areaDesc"),
            "source": source,
        }

        if item["title"] or item["summary"]:
            items.append(item)

    # A CAP XML document may contain one alert rather than RSS items.
    if not items and root.tag.split("}")[-1].lower() == "alert":
        items.append(
            {
                "title": (
                    _xml_text(root, "headline")
                    or _xml_text(root, "event")
                ),
                "summary": (
                    _xml_text(root, "description")
                    or _xml_text(root, "instruction")
                ),
                "link": _xml_text(root, "web"),
                "published": _xml_text(root, "sent"),
                "expires": _xml_text(root, "expires"),
                "severity": _xml_text(root, "severity"),
                "area": _xml_text(root, "areaDesc"),
                "source": source,
            }
        )

    return items


def _active_cap_alerts(
    alerts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Exclude alerts with a valid, explicitly expired CAP expiry time."""
    now = datetime.now(timezone.utc)
    active: list[dict[str, Any]] = []

    for alert in alerts:
        expiry = str(alert.get("expires") or "").strip()

        if expiry:
            try:
                parsed = datetime.fromisoformat(
                    expiry.replace("Z", "+00:00")
                )

                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)

                if parsed.astimezone(timezone.utc) < now:
                    continue

            except (ValueError, TypeError, OverflowError):
                # Do not discard an alert solely because its expiry format
                # could not be interpreted. The source must be checked.
                pass

        active.append(alert)

    return active


def _parse_wis2_cap_items(
    payload: Any,
) -> tuple[list[dict[str, Any]], int]:
    """Extract IMD CAP XML from matching WIS2 notification records."""
    if not isinstance(payload, dict):
        return [], 0

    features = payload.get("features", payload.get("items", payload.get("data", [])))
    if isinstance(features, dict):
        features = features.get("features", features.get("items", []))
    if not isinstance(features, list):
        return [], 0

    alerts: list[dict[str, Any]] = []
    records_seen = 0

    for feature in features:
        if not isinstance(feature, dict):
            continue

        props = feature.get("properties", feature)
        if not isinstance(props, dict):
            continue

        # WIS2 versions can expose identifiers at the feature or properties
        # level, with slightly different key casing/formatting.
        metadata_id = str(
            props.get("metadata_id")
            or props.get("metadataId")
            or feature.get("metadata_id")
            or feature.get("metadataId")
            or ""
        )
        data_id = str(
            props.get("data_id")
            or props.get("dataId")
            or feature.get("data_id")
            or feature.get("dataId")
            or ""
        )
        normalized_metadata = metadata_id.casefold().replace("_", "-")
        normalized_data_id = data_id.casefold()

        if (
            IMD_CAP_METADATA_ID.casefold() not in normalized_metadata
            and "cap_alerts" not in normalized_data_id
            and "cap-alerts" not in normalized_data_id
        ):
            continue

        records_seen += 1

        content = props.get("content", feature.get("content"))
        if isinstance(content, dict):
            encoded = (
                content.get("value")
                or content.get("data")
                or content.get("content")
            )
            encoding = str(content.get("encoding") or "").casefold()
        elif isinstance(content, str):
            encoded = content
            encoding = ""
        else:
            encoded = None
            encoding = ""

        # WIS2 deployments have returned both base64-encoded CAP XML and
        # literal XML/text despite omitting the encoding field. Try the
        # declared encoding first, then a safe literal-XML fallback. Do not
        # silently count a catalogue record as a parsed alert.
        if isinstance(encoded, str) and encoded.strip():
            candidates: list[bytes] = []
            if encoding in {"base64", "base64binary", "base64-encoded"}:
                try:
                    candidates.append(base64.b64decode(encoded, validate=True))
                except (ValueError, TypeError):
                    pass
            elif encoding in {"identity", "utf-8", "utf8", "xml", "text", "text/xml", "application/xml"}:
                candidates.append(encoded.encode("utf-8"))
            else:
                # Unknown or missing encoding: first try base64, then literal
                # XML. This handles real WIS2 payload variants without
                # treating arbitrary non-XML text as a CAP alert.
                try:
                    candidates.append(base64.b64decode(encoded, validate=True))
                except (ValueError, TypeError):
                    pass
                candidates.append(encoded.encode("utf-8"))

            for decoded in candidates:
                parsed = _parse_cap_xml(
                    decoded,
                    source="IMD WIS2 CAP feed",
                )
                if parsed:
                    alerts.extend(parsed)
                    break

            if alerts and alerts[-1].get("source") == "IMD WIS2 CAP feed":
                continue

        # Some WIS2 records expose a link to the underlying CAP XML.
        links = props.get("links", feature.get("links", []))

        if not isinstance(links, list):
            continue

        for link in links:
            if not isinstance(link, dict):
                continue

            href = str(link.get("href") or "")
            parsed_url = urlparse(href)

            # Only follow HTTPS links on the official IMD WIS2 host.
            if (
                parsed_url.scheme != "https"
                or parsed_url.hostname != "wis2box.imd.gov.in"
                or parsed_url.username
                or parsed_url.password
            ):
                continue

            try:
                response = requests.get(
                    href,
                    timeout=_TIMEOUT_SECONDS,
                    verify=certifi.where(),
                    headers={
                        "Accept": "application/xml, text/xml",
                        "User-Agent": (
                            "ResQ-AI/1.0 (government-data dashboard)"
                        ),
                    },
                )
                response.raise_for_status()

                parsed = _parse_cap_xml(
                    response.content,
                    source="IMD WIS2 CAP feed",
                )

                if parsed:
                    alerts.extend(parsed)
                    break

            except requests.RequestException:
                continue

    return _active_cap_alerts(alerts), records_seen


def get_imd_public_cap_alerts() -> dict[str, Any]:
    """Fetch public IMD RSS alerts, falling back to the official WIS2 catalogue."""
    now = time.monotonic()
    cache_key = "imd-public-cap:" + IMD_PUBLIC_CAP_URL

    with _lock:
        cached = _cache.get(cache_key)

        if cached and now - cached["stored_at"] < _CACHE_SECONDS:
            return {
                "ok": cached.get("ok", True),
                "alerts": cached.get("alerts", []),
                "records_seen": cached.get("records_seen", 0),
                "rss_ok": cached.get("rss_ok", False),
                "wis2_ok": cached.get("wis2_ok", False),
                "fetched_at": cached.get("fetched_at"),
                "cached": True,
                "error": cached.get("error"),
                "source_url": cached.get(
                    "source_url",
                    IMD_PUBLIC_CAP_URL,
                ),
            }

    errors: list[str] = []
    alerts: list[dict[str, Any]] = []
    records_seen = 0
    rss_ok = False
    wis2_ok = False
    source_url = IMD_PUBLIC_CAP_URL

    # First attempt: public IMD CAP/RSS feed.
    try:
        response = requests.get(
            IMD_PUBLIC_CAP_URL,
            headers={
                "Accept": "application/rss+xml, application/xml, text/xml",
                "User-Agent": "ResQ-AI/1.0 (government-data dashboard)",
            },
            timeout=_TIMEOUT_SECONDS,
            verify=certifi.where(),
        )
        response.raise_for_status()

        rss_ok = True
        parsed_rss = _parse_cap_xml(
            response.content,
            source="IMD public CAP feed",
        )
        records_seen = len(parsed_rss)
        alerts = _active_cap_alerts(parsed_rss)

    except requests.RequestException as exc:
        errors.append(
            f"IMD RSS: {type(exc).__name__}: {str(exc)[:180]}"
        )

    # Second attempt: official WIS2 catalogue if RSS has no active alerts.
    if not alerts:
        source_url = IMD_WIS2_CAP_URL

        try:
            response = requests.get(
                IMD_WIS2_CAP_URL,
                params={"limit": 100, "f": "json", "sortby": "-datetime"},
                headers={
                    "Accept": "application/geo+json, application/json",
                    "User-Agent": "ResQ-AI/1.0 (government-data dashboard)",
                },
                timeout=_TIMEOUT_SECONDS,
                verify=certifi.where(),
            )
            response.raise_for_status()

            wis2_ok = True
            alerts, records_seen = _parse_wis2_cap_items(
                response.json()
            )

        except (requests.RequestException, ValueError) as exc:
            errors.append(
                f"IMD WIS2 CAP: {type(exc).__name__}: {str(exc)[:180]}"
            )

    fetched_at = _now()

    if alerts:
        error = None
    elif errors:
        error = (
            "No active alerts parsed. "
            + "; ".join(errors)
        )
    else:
        error = None

    result = {
        "ok": rss_ok or wis2_ok,
        "rss_ok": rss_ok,
        "wis2_ok": wis2_ok,
        "alerts": alerts,
        "records_seen": records_seen,
        "fetched_at": fetched_at,
        "cached": False,
        "error": error,
        "source_url": source_url,
    }

    with _lock:
        _cache[cache_key] = {
            **result,
            "stored_at": now,
        }

    return result




USGS_EARTHQUAKE_FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"


def get_usgs_india_earthquakes() -> dict[str, Any]:
    """Fetch recent USGS earthquake events inside an India-region bounding box."""
    now = time.monotonic()
    cache_key = "usgs-india-earthquakes:" + USGS_EARTHQUAKE_FEED_URL

    with _lock:
        cached = _cache.get(cache_key)
        if cached and now - cached["stored_at"] < _CACHE_SECONDS:
            return {
                "source": "USGS Earthquake Hazards Program",
                "source_url": USGS_EARTHQUAKE_FEED_URL,
                "ok": cached["ok"],
                "events": cached["events"],
                "fetched_at": cached["fetched_at"],
                "cached": True,
                "error": cached.get("error"),
                "records_seen": cached.get("records_seen", 0),
            }

    try:
        response = requests.get(
            USGS_EARTHQUAKE_FEED_URL,
            headers={
                "Accept": "application/geo+json, application/json",
                "User-Agent": "ResQ-AI/1.0 (disaster-awareness dashboard)",
            },
            timeout=_TIMEOUT_SECONDS,
            verify=certifi.where(),
        )
        response.raise_for_status()
        payload = response.json()
        features = payload.get("features", []) if isinstance(payload, dict) else []
        events: list[dict[str, Any]] = []
        records_seen = len(features) if isinstance(features, list) else 0

        # This is a geographic filter, not a claim of complete Indian seismic coverage.
        for feature in features if isinstance(features, list) else []:
            if not isinstance(feature, dict):
                continue
            props = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            coords = geometry.get("coordinates", []) if isinstance(geometry, dict) else []
            if not isinstance(props, dict) or len(coords) < 2:
                continue
            try:
                longitude, latitude = float(coords[0]), float(coords[1])
            except (TypeError, ValueError):
                continue
            if not (67.0 <= longitude <= 98.0 and 5.0 <= latitude <= 38.0):
                continue
            depth = coords[2] if len(coords) > 2 else None
            try:
                depth_text = f"{float(depth):.1f} km" if depth is not None else "unknown"
            except (TypeError, ValueError):
                depth_text = "unknown"
            magnitude = props.get("mag")
            timestamp = props.get("time")
            try:
                published = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).replace(microsecond=0).isoformat()
            except (TypeError, ValueError, OverflowError, OSError):
                published = None
            events.append({
                "title": str(props.get("title") or "Earthquake event"),
                "summary": f"Magnitude {magnitude if magnitude is not None else 'unknown'} · Depth {depth_text}",
                "place": str(props.get("place") or "Location not supplied"),
                "magnitude": magnitude,
                "latitude": latitude,
                "longitude": longitude,
                "depth_km": depth,
                "published": published,
                "link": str(props.get("url") or ""),
                "source": "USGS Earthquake Hazards Program",
            })

        result = {
            "source": "USGS Earthquake Hazards Program",
            "source_url": USGS_EARTHQUAKE_FEED_URL,
            "ok": True,
            "events": events,
            "fetched_at": _now(),
            "cached": False,
            "error": None,
            "records_seen": records_seen,
        }
    except (requests.RequestException, ValueError, TypeError) as exc:
        result = {
            "source": "USGS Earthquake Hazards Program",
            "source_url": USGS_EARTHQUAKE_FEED_URL,
            "ok": False,
            "events": [],
            "fetched_at": None,
            "cached": False,
            "error": f"USGS earthquake feed unavailable: {type(exc).__name__}",
            "records_seen": 0,
        }

    with _lock:
        _cache[cache_key] = {**result, "stored_at": now}
    return result


def get_imd_live_data(
    state: str = "",
    district: str = "",
) -> dict[str, Any]:
    """Fetch authenticated IMD district data and public CAP alerts."""
    api_base = _setting("IMD_API_BASE", IMD_API_BASE).rstrip("/")
    token = _setting("IMD_API_TOKEN")

    nowcast = _cached_get_json(
        f"{api_base}/districtnowcast",
        token,
    )
    warnings = _cached_get_json(
        f"{api_base}/districtwarning",
        token,
    )

    nowcast["rows"] = _clean_rows(
        nowcast["rows"],
        state,
        district,
    )
    warnings["rows"] = _clean_rows(
        warnings["rows"],
        state,
        district,
    )

    # Always fetch the public feed. It supplements the authenticated API;
    # having a token must not disable public CAP alerts.
    public_alerts = get_imd_public_cap_alerts()

    successful = sum(
        bool(item.get("ok"))
        for item in (nowcast, warnings)
    )

    successful_times = [
        item["fetched_at"]
        for item in (nowcast, warnings, public_alerts)
        if item.get("fetched_at")
    ]

    return {
        "source": "India Meteorological Department (IMD)",
        "source_url": IMD_REFERENCE,
        "portal_url": IMD_API_PORTAL,
        "configured": bool(token),
        "ok": successful > 0 or bool(public_alerts.get("ok")),
        "fetched_at": max(successful_times, default=None),
        "nowcast": nowcast,
        "warnings": warnings,
        "public_alerts": public_alerts,
        "state_filter": state,
        "district_filter": district,
        "note": (
            "Official weather warnings are contextual hazard signals. "
            "They are not verified rescue incidents and do not alter "
            "incident scores."
        ),
    }


def get_ndma_cap_alerts() -> dict[str, Any]:
    """Fetch the authorized SACHET CAP feed URL or build it from an issued identifier."""
    url = _setting("NDMA_CAP_FEED_URL")
    identifier = _setting("NDMA_CAP_IDENTIFIER")

    # SACHET's official integration guide documents this endpoint pattern.
    # The identifier must be supplied by SACHET; never guess one.
    if not url and identifier:
        url = (
            "https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile"
            f"?identifier={quote(identifier, safe='')}"
        )

    if not url:
        return {
            "source": "NDMA SACHET / India CAP",
            "source_url": NDMA_PORTAL,
            "ok": False,
            "configured": False,
            "alerts": [],
            "fetched_at": None,
            "cached": False,
            "error": (
                "NDMA_CAP_FEED_URL is missing. Obtain the authorized "
                "CAP/RSS feed URL from SACHET; the app will not guess "
                "a feed identifier."
            ),
        }

    parsed = urlparse(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname
        not in {
            "sachet.ndma.gov.in",
            "www.sachet.ndma.gov.in",
        }
        or parsed.username
        or parsed.password
    ):
        return {
            "source": "NDMA SACHET / India CAP",
            "source_url": NDMA_PORTAL,
            "ok": False,
            "configured": True,
            "alerts": [],
            "fetched_at": None,
            "cached": False,
            "error": (
                "For safety, the feed URL must use HTTPS on "
                "sachet.ndma.gov.in."
            ),
        }

    now = time.monotonic()
    cache_key = "ndma:" + url

    with _lock:
        cached = _cache.get(cache_key)

        if cached and now - cached["stored_at"] < _CACHE_SECONDS:
            return {
                "source": "NDMA SACHET / India CAP",
                "source_url": url,
                "ok": True,
                "configured": True,
                "alerts": cached["alerts"],
                "fetched_at": cached["fetched_at"],
                "cached": True,
                "error": None,
            }

    headers = {
        "Accept": "application/rss+xml, application/xml, text/xml",
        "User-Agent": "ResQ-AI/1.0 (government-data dashboard)",
    }

    if cached and cached.get("etag"):
        headers["If-None-Match"] = cached["etag"]

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=_TIMEOUT_SECONDS,
            verify=certifi.where(),
        )

        if response.status_code == 304 and cached:
            with _lock:
                cached["stored_at"] = now

            return {
                "source": "NDMA SACHET / India CAP",
                "source_url": url,
                "ok": True,
                "configured": True,
                "alerts": cached["alerts"],
                "fetched_at": cached["fetched_at"],
                "cached": True,
                "error": None,
            }

        response.raise_for_status()

        alerts = _active_cap_alerts(
            _parse_cap_xml(
                response.content,
                source="NDMA SACHET CAP feed",
            )
        )
        fetched_at = _now()

        with _lock:
            _cache[cache_key] = {
                "alerts": alerts,
                "fetched_at": fetched_at,
                "stored_at": now,
                "etag": response.headers.get("ETag"),
            }

        return {
            "source": "NDMA SACHET / India CAP",
            "source_url": url,
            "ok": True,
            "configured": True,
            "alerts": alerts,
            "fetched_at": fetched_at,
            "cached": False,
            "error": None,
        }

    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", "unknown")
        message = (
            f"NDMA feed request failed (HTTP {status}). "
            "Verify the authorized feed URL and access."
        )

    except requests.exceptions.SSLError as exc:
        detail = " ".join(str(exc).split())[:240]
        message = (
            "NDMA TLS connection failed. SSL verification remains enabled. "
            f"Underlying error: {detail or type(exc).__name__}. "
            "Check the app logs and whether the host accepts connections "
            "from the deployed runtime."
        )

    except requests.RequestException as exc:
        detail = " ".join(str(exc).split())
        detail = detail.replace(
            url,
            f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
        )

        if len(detail) > 320:
            detail = detail[:317] + "..."

        message = (
            f"Could not retrieve NDMA feed: {type(exc).__name__}: {detail}. "
            "Check TLS certificate verification, feed availability, "
            "and network access."
        )

    return {
        "source": "NDMA SACHET / India CAP",
        "source_url": url,
        "ok": False,
        "configured": True,
        "alerts": [],
        "fetched_at": None,
        "cached": False,
        "error": message,
    }
