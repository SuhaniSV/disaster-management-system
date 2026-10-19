"""Official live-data adapters for IMD weather warnings and NDMA CAP alerts.

These feeds are kept separate from operator-reported incidents: a weather alert is
not automatically an incident and never changes deterministic incident scores.
"""
from __future__ import annotations

import os
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests

IMD_API_BASE = os.getenv("IMD_API_BASE", "https://api.imd.gov.in/api/v1").rstrip("/")
IMD_API_PORTAL = "https://api.imd.gov.in/public/index.php"
IMD_REFERENCE = "https://api.imd.gov.in/public/api_reference.html"
NDMA_PORTAL = "https://sachet.ndma.gov.in/"
NDMA_FEED_GUIDE = "https://sachet.ndma.gov.in/CapFeed"

_TIMEOUT_SECONDS = 12
_CACHE_SECONDS = 300
_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _as_rows(payload: Any) -> list[dict[str, Any]]:
    """Normalize the list and common wrapped response shapes used by public APIs."""
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
    now = time.monotonic()
    with _lock:
        cached = _cache.get(url)
        if cached and now - cached["stored_at"] < _CACHE_SECONDS:
            return {"ok": True, "rows": cached["rows"], "fetched_at": cached["fetched_at"], "cached": True, "error": None}
    if not token:
        return {"ok": False, "rows": [], "fetched_at": None, "cached": False,
                "error": "IMD API credentials are not configured. Register at the official IMD API portal and set IMD_API_TOKEN."}
    header_name = os.getenv("IMD_API_AUTH_HEADER", "Authorization").strip() or "Authorization"
    scheme = os.getenv("IMD_API_AUTH_SCHEME", "Bearer").strip()
    auth_value = f"{scheme} {token}".strip()
    try:
        response = requests.get(
            url,
            headers={header_name: auth_value, "Accept": "application/json", "User-Agent": "ResQ-AI/1.0 (government-data dashboard)"},
            timeout=_TIMEOUT_SECONDS,
        )
        if response.status_code == 304 and cached:
            with _lock:
                cached["stored_at"] = now
            return {"ok": True, "rows": cached["rows"], "fetched_at": cached["fetched_at"], "cached": True, "error": None}
        response.raise_for_status()
        payload = response.json()
        rows = _as_rows(payload)
        fetched_at = _now()
        with _lock:
            _cache[url] = {"rows": rows, "fetched_at": fetched_at, "stored_at": now, "etag": response.headers.get("ETag")}
        return {"ok": True, "rows": rows, "fetched_at": fetched_at, "cached": False, "error": None}
    except requests.HTTPError as exc:
        status = getattr(exc.response, "status_code", "unknown")
        if status in (401, 403):
            message = f"IMD rejected the credentials (HTTP {status}). Check your issued token and auth header settings."
        else:
            message = f"IMD request failed (HTTP {status})."
    except (requests.RequestException, ValueError) as exc:
        message = f"Could not retrieve valid IMD data: {type(exc).__name__}."
    return {"ok": False, "rows": [], "fetched_at": None, "cached": False, "error": message}


def _matches(row: dict[str, Any], state: str = "", district: str = "") -> bool:
    state_text = " ".join(str(row.get(key, "")) for key in ("State", "STATE", "state", "state_name")).casefold()
    district_text = " ".join(str(row.get(key, "")) for key in ("District", "DISTRICT", "district", "district_name", "Station", "station")).casefold()
    return (not state or state.casefold() in state_text) and (not district or district.casefold() in district_text)


def _clean_rows(rows: list[dict[str, Any]], state: str = "", district: str = "") -> list[dict[str, Any]]:
    return [row for row in rows if _matches(row, state, district)]


def get_imd_live_data(state: str = "", district: str = "") -> dict[str, Any]:
    """Fetch IMD district nowcasts and five-day district warnings."""
    token = os.getenv("IMD_API_TOKEN", "").strip()
    nowcast = _cached_get_json(f"{IMD_API_BASE}/districtnowcast", token)
    warnings = _cached_get_json(f"{IMD_API_BASE}/districtwarning", token)
    nowcast["rows"] = _clean_rows(nowcast["rows"], state, district)
    warnings["rows"] = _clean_rows(warnings["rows"], state, district)
    configured = bool(token)
    successful = sum(bool(item["ok"]) for item in (nowcast, warnings))
    return {
        "source": "India Meteorological Department (IMD)",
        "source_url": IMD_REFERENCE,
        "portal_url": IMD_API_PORTAL,
        "configured": configured,
        "ok": successful > 0,
        "fetched_at": max((item["fetched_at"] for item in (nowcast, warnings) if item["fetched_at"]), default=None),
        "nowcast": nowcast,
        "warnings": warnings,
        "state_filter": state,
        "district_filter": district,
        "note": "Official weather warnings are contextual hazard signals. They are not verified rescue incidents and do not alter incident scores.",
    }


def _xml_text(element: ET.Element, local_name: str) -> str:
    for child in element.iter():
        if child.tag.split("}")[-1].lower() == local_name.lower() and child.text:
            return child.text.strip()
    return ""


def _parse_cap_xml(content: bytes) -> list[dict[str, Any]]:
    """Parse RSS items or CAP alert XML without assuming one feed wrapper."""
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
            "source": "NDMA SACHET CAP feed",
        }
        if item["title"] or item["summary"]:
            items.append(item)
    if not items and root.tag.split("}")[-1].lower() == "alert":
        items.append({
            "title": _xml_text(root, "headline") or _xml_text(root, "event"),
            "summary": _xml_text(root, "description") or _xml_text(root, "instruction"),
            "link": _xml_text(root, "web"),
            "published": _xml_text(root, "sent"),
            "source": "NDMA SACHET CAP feed",
        })
    return items


def get_ndma_cap_alerts() -> dict[str, Any]:
    """Fetch an NDMA SACHET CAP/RSS feed URL supplied by the user/agency.

    SACHET's official agency guide requires ETag-aware caching. We honor ETag
    validators and reuse the last parsed response on HTTP 304.
    """
    url = os.getenv("NDMA_CAP_FEED_URL", "").strip()
    if not url:
        return {
            "source": "NDMA SACHET / India CAP",
            "source_url": NDMA_PORTAL,
            "ok": False,
            "configured": False,
            "alerts": [],
            "fetched_at": None,
            "error": "Configure NDMA_CAP_FEED_URL with the authorized CAP/RSS feed URL supplied by SACHET. The official guide uses a feed identifier; do not guess it.",
        }
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"sachet.ndma.gov.in", "www.sachet.ndma.gov.in"}:
        return {"source": "NDMA SACHET / India CAP", "source_url": NDMA_PORTAL, "ok": False, "configured": True,
                "alerts": [], "fetched_at": None, "error": "For safety, NDMA feed URL must use HTTPS on sachet.ndma.gov.in."}
    now = time.monotonic()
    with _lock:
        cached = _cache.get("ndma:" + url)
    headers = {"Accept": "application/rss+xml, application/xml, text/xml", "User-Agent": "ResQ-AI/1.0 (government-data dashboard)"}
    if cached and cached.get("etag"):
        headers["If-None-Match"] = cached["etag"]
    try:
        response = requests.get(url, headers=headers, timeout=_TIMEOUT_SECONDS)
        if response.status_code == 304 and cached:
            with _lock:
                cached["stored_at"] = now
            return {"source": "NDMA SACHET / India CAP", "source_url": url, "ok": True, "configured": True,
                    "alerts": cached["alerts"], "fetched_at": cached["fetched_at"], "cached": True, "error": None}
        response.raise_for_status()
        alerts = _parse_cap_xml(response.content)
        fetched_at = _now()
        with _lock:
            _cache["ndma:" + url] = {"alerts": alerts, "fetched_at": fetched_at, "stored_at": now, "etag": response.headers.get("ETag")}
        return {"source": "NDMA SACHET / India CAP", "source_url": url, "ok": True, "configured": True,
                "alerts": alerts, "fetched_at": fetched_at, "cached": False, "error": None}
    except requests.RequestException as exc:
        return {"source": "NDMA SACHET / India CAP", "source_url": url, "ok": False, "configured": True,
                "alerts": [], "fetched_at": None, "error": f"Could not retrieve NDMA feed: {type(exc).__name__}."}
