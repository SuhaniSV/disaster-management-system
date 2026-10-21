"""Best-effort English rendering for official alert text.

Original records and source links remain unchanged in the data layer. Translation is
cached. If translation fails, the display string is empty so the UI can omit that alert
instead of showing a fake alert headline or leaking regional-language text.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any

# Common scripts used in Indian government alerts; English text and Latin-script
# place names pass through unchanged.
_NON_LATIN_LETTERS = re.compile(
    r"[\u0900-\u097F\u0980-\u09FF\u0A00-\u0A7F\u0A80-\u0AFF"
    r"\u0B00-\u0B7F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF"
    r"\u0D00-\u0D7F\u0D80-\u0DFF\u0E00-\u0E7F\u0E80-\u0EFF"
    r"\u0F00-\u0FFF\u1000-\u109F\u1780-\u17FF\u3040-\u30FF"
    r"\u3400-\u9FFF]"
)
_PRESERVE_KEYS = {
    "link", "url", "source_url", "source", "published", "expires", "sent",
    "id", "identifier", "guid", "latitude", "longitude", "lat", "lon",
    "coordinates", "fetched_at", "timestamp", "date", "time",
}


@lru_cache(maxsize=2048)
def _translate_cached(text: str) -> str:
    """Translate one non-English string; return empty on failure so UI can omit it."""
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="auto", target="en").translate(text)
        if isinstance(translated, str) and translated.strip():
            # Guard against a translator returning the original non-English text.
            result = translated.strip()
            if not _NON_LATIN_LETTERS.search(result):
                return result
    except Exception:
        pass
    return ""


def english_text(value: Any) -> str:
    """Return English text, or an empty string when translation fails."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if not _NON_LATIN_LETTERS.search(text):
        return text
    return _translate_cached(text)


def english_record(record: Any) -> Any:
    """Translate displayable text recursively while preserving URLs and timestamps."""
    if isinstance(record, dict):
        result = {}
        for key, value in record.items():
            if key.casefold() in _PRESERVE_KEYS:
                result[key] = value
            else:
                result[key] = english_record(value)
        return result
    if isinstance(record, list):
        return [english_record(item) for item in record]
    if isinstance(record, str):
        return english_text(record)
    return record
