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
from urllib.parse import urlparse

import certifi
import requests

IMD_API_BASE = os.getenv("IMD_API_BASE", "https://api.imd.gov.in/api/v1").rstrip("/")
IMD_API_PORTAL = "https://api.imd.gov.in/public/index.php"
IMD_REFERENCE = "https://api.imd.gov.in/public/api_reference.html"
# Public CAP/RSS alerts linked directly from the official IMD Mausam website.
IMD_PUBLIC_CAP_URL = "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml"
IMD_WIS2_CAP_URL = "https://wis2box.imd.gov.in/oapi/collections/messages/items"
IMD_CAP_METADATA_ID = "urn:wmo:md:in-imd:cap_alerts"
NDMA_PORTAL = "https://sachet.ndma.gov.in/"
NDMA_FEED_GUIDE = "https://sachet.ndma.gov.in/CapFeed"

_TIMEOUT_SECONDS = 12
_CACHE_SECONDS = 300
_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] = {}


def _now() -> str:
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
                    if isinstance(value.get(nested), list):
                        return [row for row in value[nested] if isinstance(row, dict)]
        return [payload] if payload else []
    return []


def _cached_get_json(url: str, token: str) -> dict[str, Any]:
    """Fetch JSON with a five-minute cache scoped to the credential used."""
    if not token:
        return {
            "ok": False, "rows": [], "fetched_at": None, "cached": False,
            "error": "IMD_API_TOKEN is missing. Obtain an issued token from the official IMD API portal and configure it in the app's secrets.",
        }

    # Never store the token itself in the cache key.
    cache_key = f"{url}:{hashlib.sha256(token.encode('utf-8')).hexdigest()}"
    now = time.monotonic()
    with _lock:
        cached = _cache.get(cache_key)
        if cached and now - cached["stored_at"] < _CACHE_SECONDS:
            return {
                "ok": True, "rows": cached["rows"], "fetched_at": cached["fetched_at"],
                "cached": True, "error": None,
            }

    header_name = _setting("IMD_API_AUTH_HEADER", "Authorization").strip() or "Authorization"
    scheme = _setting("IMD_API_AUTH_SCHEME", "Bearer").strip()
    auth_value = f"{scheme} {token}".strip()
    try:
        response = requests.get(
            url,
            headers={
                header_name: auth_value,
                "Accept": "application/json",
                "User-Agent": "ResQ-AI/1.0 (government-data dashboard)",
            },
            timeout=_TIMEOUT_SECONDS,
        )
        if response.status_code == 304 and cached:
            with _lock:
                cached["stored_at"] = now
            return {
                "ok": True, "rows": cached["rows"], "fetched_at": cached["fetched_at"],
                "cached": True, "error": None,
            }
        response.raise_for_status()
        payload = response.json()
        rows = _as_rows(payload)
        fetched_at = _now()
        with _lock:
            _cache[cache_key] = {
                "rows": rows, "fetched_at": fetched_at, "stored_at": now,
                "etag": response.headers.get("ETag"),
            }
        return {"ok": True, "rows": rows, "fetched_at": fetched_at, "cached": False, "error": None}
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", "unknown")
        if status in (401, 403):
            message = f"IMD rejected the credentials (HTTP {status}). Check the issued token, permissions, and documented auth header."
        else:
            message = f"IMD request failed (HTTP {status}). Check endpoint access and the current IMD API reference."
    except (requests.RequestException, ValueError) as exc:
        message = f"Could not retrieve valid IMD data: {type(exc).__name__}. Check network access and the official API response format."
    return {"ok": False, "rows": [], "fetched_at": None, "cached": False, "error": message}


def _matches(row: dict[str, Any], state: str = "", district: str = "") -> bool:
    state_text = " ".join(str(row.get(key, "")) for key in ("State", "STATE", "state", "state_name")).casefold()
    district_text = " ".join(
        str(row.get(key, ""))
        for key in ("District", "DISTRICT", "district", "district_name", "Station", "station")
    ).casefold()
    return (not state or state.casefold() in state_text) and (not district or district.casefold() in district_text)


def _clean_rows(rows: list[dict[str, Any]], state: str = "", district: str = "") -> list[dict[str, Any]]:
    return [row for row in rows if _matches(row, state, district)]


def get_imd_live_data(state: str = "", district: str = "") -> dict[str, Any]:
    """Fetch IMD district nowcasts and warnings using the configured official API."""
    api_base = _setting("IMD_API_BASE", IMD_API_BASE).rstrip("/")
    token = _setting("IMD_API_TOKEN")
    nowcast = _cached_get_json(f"{api_base}/districtnowcast", token)
    warnings = _cached_get_json(f"{api_base}/districtwarning", token)
    nowcast["rows"] = _clean_rows(nowcast["rows"], state, district)
    warnings["rows"] = _clean_rows(warnings["rows"], state, district)
    public_alerts = (
        {"ok": False, "alerts": [], "fetched_at": None, "cached": False,
         "error": None, "source_url": IMD_PUBLIC_CAP_URL}
        if token else get_imd_public_cap_alerts()
    )
    successful = sum(bool(item["ok"]) for item in (nowcast, warnings))
    successful_times = [
        item["fetched_at"] for item in (nowcast, warnings, public_alerts)
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
        "note": "Official weather warnings are contextual hazard signals. They are not verified rescue incidents and do not alter incident scores.",
    }


def _xml_text(element: ET.Element, local_name: str) -> str:
    for child in element.iter():
        if child.tag.split("}")[-1].lower() == local_name.lower() and child.text:
            return child.text.strip()
    return ""


def _parse_cap_xml(content: bytes, source: str = "NDMA SACHET CAP feed") -> list[dict[str, Any]]:
    """Parse RSS item XML or a single CAP alert XML document."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []
    items: list[dict[str, Any]] = []
    rss_items = [node for node in root.iter() if node.tag.split("}")[-1].lower() == "item"]
    for node in rss_items:
        item = {
            "title": _xml_text(node, "title"),
            "summary": _xml_text(node, "description"),
            "link": _xml_text(node, "link"),
            "published": _xml_text(node, "pubDate"),
            "expires": _xml_text(node, "expires"),
            "severity": _xml_text(node, "severity"),
            "area": _xml_text(node, "areaDesc"),
            "source": source,
        }
        if item["title"] or item["summary"]:
            items.append(item)
    if not items and root.tag.split("}")[-1].lower() == "alert":
        items.append({
            "title": _xml_text(root, "headline") or _xml_text(root, "event"),
            "summary": _xml_text(root, "description") or _xml_text(root, "instruction"),
            "link": _xml_text(root, "web"),
            "published": _xml_text(root, "sent"),
            "expires": _xml_text(root, "expires"),
            "severity": _xml_text(root, "severity"),
            "area": _xml_text(root, "areaDesc"),
            "source": source,
        })
    return items


def _active_cap_alerts(alerts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Exclude CAP alerts whose explicit expiry time is in the past."""
    now = datetime.now(timezone.utc)
    active = []
    for alert in alerts:
        expiry = str(alert.get("expires") or "").strip()
        if expiry:
            try:
                parsed = datetime.fromisoformat(expiry.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                if parsed.astimezone(timezone.utc) < now:
                    continue
            except ValueError:
                pass
        active.append(alert)
    return active


def _parse_wis2_cap_items(payload: Any) -> tuple[list[dict[str, Any]], int]:
    """Extract IMD CAP XML from WIS2 notification records."""
    if not isinstance(payload, dict):
        return [], 0
    features = payload.get("features", payload.get("items", []))
    if not isinstance(features, list):
        return [], 0
    alerts: list[dict[str, Any]] = []
    seen = 0
    for feature in features:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties", feature)
        if not isinstance(props, dict):
            continue
        metadata_id = str(props.get("metadata_id") or props.get("metadataId") or "")
        data_id = str(props.get("data_id") or props.get("dataId") or "")
        if metadata_id != IMD_CAP_METADATA_ID and "cap_alerts" not in data_id:
            continue
        seen += 1
        content = props.get("content")
        encoded = content.get("value") if isinstance(content, dict) else None
        if isinstance(encoded, str) and encoded:
            try:
                xml_content = base64.b64decode(encoded).decode("utf-8", errors="replace").encode("utf-8")
                alerts.extend(_parse_cap_xml(xml_content, source="IMD WIS2 CAP feed"))
                continue
            except (ValueError, TypeError):
                pass
        links = props.get("links", feature.get("links", []))
        if isinstance(links, list):
            for link in links:
                if not isinstance(link, dict):
                    continue
                href = str(link.get("href") or "")
                if not href.startswith("https://wis2box.imd.gov.in/"):
                    continue
                try:
                    response = requests.get(href, timeout=_TIMEOUT_SECONDS, verify=certifi.where())
                    response.raise_for_status()
                    parsed = _parse_cap_xml(response.content, source="IMD WIS2 CAP feed")
                    if parsed:
                        alerts.extend(parsed)
                        break
                except requests.RequestException:
                    continue
    return _active_cap_alerts(alerts), seen


def get_imd_public_cap_alerts() -> dict[str, Any]:
    """Use the public IMD RSS feed, then the official IMD WIS2 CAP catalogue if RSS is empty."""
    now = time.monotonic()
    cache_key = "imd-public-cap:" + IMD_PUBLIC_CAP_URL
    with _lock:
        cached = _cache.get(cache_key)
        if cached and now - cached["stored_at"] < _CACHE_SECONDS:
            return {
                "ok": cached.get("ok", True), "alerts": cached["alerts"], "records_seen": cached.get("records_seen", len(cached["alerts"])),
                "rss_ok": cached.get("rss_ok", False), "wis2_ok": cached.get("wis2_ok", False),
                "fetched_at": cached["fetched_at"], "cached": True, "error": cached.get("error"),
                "source_url": cached.get("source_url", IMD_PUBLIC_CAP_URL),
            }

    errors: list[str] = []
    alerts: list[dict[str, Any]] = []
    records_seen = 0
    rss_ok = False
    wis2_ok = False
    etag = None
    source_url = IMD_PUBLIC_CAP_URL
    try:
        response = requests.get(
            IMD_PUBLIC_CAP_URL,
            headers={"Accept": "application/rss+xml, application/xml, text/xml",
                     "User-Agent": "ResQ-AI/1.0 (government-data dashboard)"},
            timeout=_TIMEOUT_SECONDS,
            verify=certifi.where(),
        )
        response.raise_for_status()
        rss_ok = True
        etag = response.headers.get("ETag")
        parsed_rss = _parse_cap_xml(response.content, source="IMD public CAP feed")
        records_seen = len(parsed_rss)
        alerts = _active_cap_alerts(parsed_rss)
    except requests.RequestException as exc:
        errors.append(f"IMD RSS: {type(exc).__name__}: {str(exc)[:180]}")

    if not alerts:
        source_url = IMD_WIS2_CAP_URL
        try:
            response = requests.get(
                IMD_WIS2_CAP_URL,
                params={"limit": 100, "f": "json"},
                headers={"Accept": "application/geo+json, application/json",
                         "User-Agent": "ResQ-AI/1.0 (government-data dashboard)"},
                timeout=_TIMEOUT_SECONDS,
                verify=certifi.where(),
            )
            response.raise_for_status()
            wis2_ok = True
            alerts, records_seen = _parse_wis2_cap_items(response.json())
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"IMD WIS2 CAP: {type(exc).__name__}: {str(exc)[:180]}")

    fetched_at = _now()
    error = None if alerts else ("No active alerts parsed. " + "; ".join(errors) if errors else None)
    result = {
        "ok": rss_ok or wis2_ok, "rss_ok": rss_ok, "wis2_ok": wis2_ok,
        "alerts": alerts, "records_seen": records_seen,
        "fetched_at": fetched_at, "cached": False, "error": error,
        "source_url": source_url,
    }
    with _lock:
        _cache[cache_key] = {
            "alerts": alerts, "records_seen": records_seen, "fetched_at": fetched_at,
            "stored_at": now, "etag": etag, "error": error, "source_url": source_url,
            "ok": rss_ok or wis2_ok, "rss_ok": rss_ok, "wis2_ok": wis2_ok,
        }
    return result


def get_ndma_cap_alerts() -> dict[str, Any]:
    """Fetch a CAP/RSS URL supplied by SACHET or an authorized agency."""
    url = _setting("NDMA_CAP_FEED_URL")
    if not url:
        return {
            "source": "NDMA SACHET / India CAP",
            "source_url": NDMA_PORTAL,
            "ok": False,
            "configured": False,
            "alerts": [],
            "fetched_at": None,
            "error": "NDMA_CAP_FEED_URL is missing. Obtain the authorized CAP/RSS feed URL from SACHET; the app will not guess a feed identifier.",
        }

    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"sachet.ndma.gov.in", "www.sachet.ndma.gov.in"}:
        return {
            "source": "NDMA SACHET / India CAP", "source_url": NDMA_PORTAL,
            "ok": False, "configured": True, "alerts": [], "fetched_at": None,
            "error": "For safety, the feed URL must use HTTPS on sachet.ndma.gov.in.",
        }

    now = time.monotonic()
    cache_key = "ndma:" + url
    with _lock:
        cached = _cache.get(cache_key)
    headers = {
        "Accept": "application/rss+xml, application/xml, text/xml",
        "User-Agent": "ResQ-AI/1.0 (government-data dashboard)",
    }
    if cached and cached.get("etag"):
        headers["If-None-Match"] = cached["etag"]
    try:
        response = requests.get(url, headers=headers, timeout=_TIMEOUT_SECONDS)
        if response.status_code == 304 and cached:
            with _lock:
                cached["stored_at"] = now
            return {
                "source": "NDMA SACHET / India CAP", "source_url": url, "ok": True,
                "configured": True, "alerts": cached["alerts"], "fetched_at": cached["fetched_at"],
                "cached": True, "error": None,
            }
        response.raise_for_status()
        alerts = _parse_cap_xml(response.content)
        fetched_at = _now()
        with _lock:
            _cache[cache_key] = {
                "alerts": alerts, "fetched_at": fetched_at, "stored_at": now,
                "etag": response.headers.get("ETag"),
            }
        return {
            "source": "NDMA SACHET / India CAP", "source_url": url, "ok": True,
            "configured": True, "alerts": alerts, "fetched_at": fetched_at,
            "cached": False, "error": None,
        }
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", "unknown")
        message = f"NDMA feed request failed (HTTP {status}). Verify the authorized feed URL and access."
    except requests.exceptions.SSLError as exc:
        # Preserve certificate verification; include a short, sanitized TLS detail so
        # deployment diagnostics can distinguish certificate, hostname, and handshake failures.
        detail = " ".join(str(exc).split())[:240]
        message = (
            "NDMA TLS connection failed. SSL verification remains enabled. "
            f"Underlying error: {detail or type(exc).__name__}. "
            "If this only occurs on Streamlit Cloud, check the app logs and whether the "
            "host accepts connections from the Cloud runtime."
        )
    except requests.RequestException as exc:
        message = f"Could not retrieve NDMA feed: {type(exc).__name__}. Check feed availability and network access."
    return {
        "source": "NDMA SACHET / India CAP", "source_url": url, "ok": False,
        "configured": True, "alerts": [], "fetched_at": None, "error": message,
    }
