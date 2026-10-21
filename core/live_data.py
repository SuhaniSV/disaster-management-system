"""Official live-data adapters for IMD weather warnings and NDMA CAP alerts.

These read-only feeds remain separate from operator-reported incidents and never
change deterministic incident scores or dispatch resources.
"""
from __future__ import annotations

import hashlib
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
# Public CAP/RSS alerts linked directly from the official IMD Mausam website.
IMD_PUBLIC_CAP_URL = "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml"
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
            "source": "NDMA SACHET CAP feed",
        })
    return items


def get_imd_public_cap_alerts() -> dict[str, Any]:
    """Fetch the public IMD CAP/RSS feed linked from IMD's official website."""
    now = time.monotonic()
    cache_key = "imd-public-cap:" + IMD_PUBLIC_CAP_URL
    with _lock:
        cached = _cache.get(cache_key)
        if cached and now - cached["stored_at"] < _CACHE_SECONDS:
            return {
                "ok": True, "alerts": cached["alerts"], "fetched_at": cached["fetched_at"],
                "cached": True, "error": None, "source_url": IMD_PUBLIC_CAP_URL,
            }

    headers = {
        "Accept": "application/rss+xml, application/xml, text/xml",
        "User-Agent": "ResQ-AI/1.0 (government-data dashboard)",
    }
    if cached and cached.get("etag"):
        headers["If-None-Match"] = cached["etag"]
    try:
        response = requests.get(IMD_PUBLIC_CAP_URL, headers=headers, timeout=_TIMEOUT_SECONDS)
        if response.status_code == 304 and cached:
            with _lock:
                cached["stored_at"] = now
            return {
                "ok": True, "alerts": cached["alerts"], "fetched_at": cached["fetched_at"],
                "cached": True, "error": None, "source_url": IMD_PUBLIC_CAP_URL,
            }
        response.raise_for_status()
        alerts = _parse_cap_xml(response.content, source="IMD public CAP feed")
        fetched_at = _now()
        with _lock:
            _cache[cache_key] = {
                "alerts": alerts, "fetched_at": fetched_at, "stored_at": now,
                "etag": response.headers.get("ETag"),
            }
        return {
            "ok": True, "alerts": alerts, "fetched_at": fetched_at,
            "cached": False, "error": None, "source_url": IMD_PUBLIC_CAP_URL,
        }
    except requests.RequestException as exc:
        return {
            "ok": False, "alerts": [], "fetched_at": None, "cached": False,
            "error": f"Could not retrieve IMD public CAP feed: {type(exc).__name__}.",
            "source_url": IMD_PUBLIC_CAP_URL,
        }


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
