"""Command-center visual theme."""

from __future__ import annotations

import streamlit as st

from core.config import DISCLAIMER, DEMO_BANNER
from core.llm_client import llm_configured
from core.state import CommandCenter, load_demo_disaster
from components.session import persist


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500&display=swap');

html, body, [class*="css"]  {
  font-family: "IBM Plex Sans", sans-serif;
}

.stApp {
  background: radial-gradient(1200px 600px at 20% -10%, #1b2a4a 0%, #0b1220 42%);
}

section[data-testid="stSidebar"] {
  background: #0d1526;
  border-right: 1px solid #243049;
}

.resq-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  padding: 8px 4px 18px 4px;
  border-bottom: 1px solid #243049;
  margin-bottom: 16px;
}

.resq-kicker {
  color: #7aa2ff;
  letter-spacing: 0.18em;
  font-size: 12px;
  font-weight: 600;
}

.resq-title {
  font-size: 28px;
  font-weight: 700;
  color: #f4f7ff;
  margin: 0;
}

.resq-sub {
  color: #9db0cc;
  margin-top: 4px;
  font-size: 14px;
}

.resq-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}

.pill {
  font-family: "IBM Plex Mono", monospace;
  font-size: 11px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid #2b3b59;
  background: #121a2b;
  color: #d5e4ff;
}

.pill.ok { border-color: #1f6f4a; color: #7dffa6; background: #10261c; }
.pill.warn { border-color: #8a6a12; color: #ffd56a; background: #2a210e; }
.pill.bad { border-color: #8a2030; color: #ff8b9a; background: #2a1014; }
.pill.demo { border-color: #35548a; color: #9ec1ff; }

.metric-card {
  background: linear-gradient(180deg, #162033 0%, #121a2b 100%);
  border: 1px solid #2a3b59;
  border-radius: 14px;
  padding: 14px 16px 12px 16px;
  min-height: 96px;
}

.metric-card .label {
  color: #8ea2c3;
  font-size: 12px;
  letter-spacing: 0.08em;
  font-weight: 600;
}

.metric-card .value {
  font-size: 30px;
  font-weight: 700;
  color: #f7fbff;
  margin-top: 6px;
  font-family: "IBM Plex Mono", monospace;
}

.metric-card.critical .value { color: #ff6b7d; }
.metric-card.medical .value { color: #ffb347; }

.panel {
  background: #121a2b;
  border: 1px solid #2a3b59;
  border-radius: 14px;
  padding: 12px 14px;
}

.event-line {
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
  color: #c5d4ee;
  padding: 4px 0;
  border-bottom: 1px solid #1c2940;
}

.disclaimer {
  color: #8ea2c3;
  font-size: 12px;
  margin-top: 10px;
}

div[data-testid="stMetric"] {
  background: #121a2b;
  border: 1px solid #2a3b59;
  border-radius: 14px;
  padding: 12px;
}

.stDataFrame { border-radius: 12px; overflow: hidden; }
</style>
"""


def inject_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def page_setup(title: str) -> None:
    st.set_page_config(
        page_title=f"ResQ-AI | {title}",
        page_icon="🆘",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme()


def render_sidebar(center: CommandCenter) -> None:
    st.sidebar.markdown("### RESQ-AI")
    st.sidebar.caption("Intelligent Disaster Command Center")
    st.sidebar.markdown(f"**{center.ai_mode}**")
    st.sidebar.markdown("**SYSTEM STATUS:** Operational")
    st.sidebar.markdown("**DEMO MODE** — simulated Pune-area data")
    st.sidebar.caption(DEMO_BANNER)
    if st.sidebar.button("LOAD DEMO DISASTER", use_container_width=True):
        persist(load_demo_disaster())
        st.sidebar.success("Flood-city demo scenario loaded.")
        st.rerun()
    st.sidebar.divider()
    st.sidebar.caption(DISCLAIMER)
    if llm_configured():
        st.sidebar.caption("LLM key detected in environment/secrets. Analysis uses the model when reachable.")
    else:
        st.sidebar.caption("No LLM key configured. Keyword fallback analysis is active.")


def render_header(center: CommandCenter, subtitle: str) -> None:
    ai_class = "ok" if "Active" in center.ai_mode else "warn"
    st.markdown(
        f"""
        <div class="resq-header">
          <div>
            <div class="resq-kicker">RESQ-AI</div>
            <h1 class="resq-title">INTELLIGENT DISASTER COMMAND CENTER</h1>
            <div class="resq-sub">{subtitle}</div>
          </div>
          <div class="resq-pills">
            <div class="pill {ai_class}">{center.ai_mode}</div>
            <div class="pill ok">SYSTEM STATUS: OPERATIONAL</div>
            <div class="pill demo">DEMO MODE</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
