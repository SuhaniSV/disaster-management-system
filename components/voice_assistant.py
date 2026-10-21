"""Browser voice UI for the ResQ Assistant.

Uses the browser's Web Speech API for speech recognition and speech synthesis.
No audio is uploaded to a third-party transcription service.
"""
from pathlib import Path

import streamlit.components.v1 as components

_FRONTEND = Path(__file__).parent / "voice_frontend"
_voice_component = components.declare_component(
    "resq_voice_assistant",
    path=str(_FRONTEND),
)


def voice_assistant(response_text: str = "", response_id: int = 0):
    """Render voice controls and return a newly recognized transcript, if any."""
    return _voice_component(
        response_text=response_text or "",
        response_id=int(response_id or 0),
        default=None,
        key="resq_voice_assistant_component",
    )
