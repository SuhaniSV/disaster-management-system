from __future__ import annotations

import os
from typing import Any

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass


def _from_streamlit(key: str) -> str | None:
    try:
        import streamlit as st

        if key in st.secrets:
            value = st.secrets.get(key)
            return str(value) if value not in (None, "") else None
        # Nested openai.api_key style
        if "openai" in st.secrets:
            block = st.secrets["openai"]
            mapping = {
                "OPENAI_API_KEY": "api_key",
                "OPENAI_BASE_URL": "base_url",
                "OPENAI_MODEL": "model",
            }
            inner = mapping.get(key)
            if inner and inner in block:
                value = block[inner]
                return str(value) if value not in (None, "") else None
    except Exception:
        return None
    return None


def get_setting(key: str, default: str = "") -> str:
    env = os.environ.get(key)
    if env:
        return env
    secret = _from_streamlit(key)
    if secret:
        return secret
    return default


def llm_configured() -> bool:
    key = get_setting("OPENAI_API_KEY")
    return bool(key and key.strip() and key.strip() not in {"your-key-here", "changeme"})


class LLMClient:
    """Thin OpenAI-compatible chat client. Never logs the API key."""

    def __init__(self) -> None:
        self.api_key = get_setting("OPENAI_API_KEY")
        self.base_url = get_setting("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.model = get_setting("OPENAI_MODEL", "gpt-4o-mini")

    def complete_json(self, system_prompt: str, user_prompt: str, timeout: int = 25) -> str:
        if not llm_configured():
            raise RuntimeError("LLM API key is not configured")
        import requests

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        # Some providers honor json_object; ignore if rejected by catching HTTP errors at caller.
        payload["response_format"] = {"type": "json_object"}
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            if response.status_code >= 400:
                payload.pop("response_format", None)
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError("LLM request failed") from exc
