from __future__ import annotations

from datetime import datetime, timezone


def make_event(message: str, category: str = "info") -> dict:
    return {
        "ts": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "message": message,
        "category": category,
    }


def format_event(event: dict) -> str:
    return f"{event.get('ts', '--:--:--')} — {event.get('message', '')}"
