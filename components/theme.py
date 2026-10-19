"""Command-center visual theme."""

from __future__ import annotations

import streamlit as st

from core.config import DISCLAIMER, DEMO_BANNER
from core.llm_client import llm_configured
from core.state import CommandCenter, load_demo_disaster
from components.session import persist


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');

:root {
  color-scheme: light;
  --resq-ink: #152238;
  --resq-muted: #66758b;
  --resq-border: #e2e8f0;
  --resq-panel: #ffffff;
  --resq-canvas: #f5f7fb;
  --resq-blue: #2457c5;
  --resq-teal: #0f766e;
  --resq-red: #c2414b;
  --resq-radius: 14px;
  --resq-shadow: 0 8px 24px rgba(22,34,56,.045);
}

html, body, [class*="css"], [data-testid="stAppViewContainer"] {
  font-family: "DM Sans", sans-serif;
  color: var(--resq-ink);
}
.stApp {
  background: var(--resq-canvas);
  color: var(--resq-ink);
}
[data-testid="stHeader"] {
  background: rgba(245,247,251,.92);
}
[data-testid="stMainBlockContainer"] {
  padding-top: 1.8rem;
  padding-bottom: 3rem;
  max-width: 1600px;
}
section[data-testid="stSidebar"] {
  background: #ffffff;
  border-right: 1px solid var(--resq-border);
}
section[data-testid="stSidebar"] > div {
  padding-top: 1.25rem;
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
  color: var(--resq-muted);
}
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
  color: var(--resq-ink);
  letter-spacing: -.03em;
}
h1, h2, h3, h4, h5 {
  color: var(--resq-ink);
  letter-spacing: -.035em;
}
h1 { font-weight: 750 !important; line-height: 1.12 !important; }
h2 { font-size: clamp(1.35rem, 1.7vw, 1.65rem) !important; }
h2, h3 { font-weight: 700 !important; }
h3 { font-size: 1.12rem !important; }
h4, h5 { font-weight: 650 !important; }
[data-testid="stMarkdownContainer"] p { line-height: 1.65; }
.stMarkdown, [data-testid="stVerticalBlock"] > [data-testid="element-container"] { scroll-margin-top: 1rem; }
::selection { background: #c9d8ff; color: #152238; }
p, label, li, [data-testid="stMarkdownContainer"] {
  color: var(--resq-ink);
}
small, .stCaption, [data-testid="stCaptionContainer"] {
  color: var(--resq-muted) !important;
}
a { color: var(--resq-blue) !important; }

.resq-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  padding: 10px 0 22px;
  border-bottom: 1px solid var(--resq-border);
  margin-bottom: 26px;
  padding-top: 14px;
  padding-bottom: 24px;
}
.resq-kicker {
  color: var(--resq-blue);
  letter-spacing: .16em;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.resq-title {
  font-size: clamp(26px, 2.3vw, 35px);
  line-height: 1.15;
  font-weight: 750;
  color: var(--resq-ink);
  margin: 0;
  letter-spacing: -.045em;
}
.resq-sub {
  color: var(--resq-muted);
  margin-top: 8px;
  font-size: 14px;
  line-height: 1.55;
  max-width: 780px;
}
.resq-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
.pill {
  font-family: "IBM Plex Mono", monospace;
  font-size: 10px;
  font-weight: 600;
  padding: 7px 10px;
  border-radius: 8px;
  border: 1px solid #dbe4f0;
  background: #f8fafc;
  color: #34445b;
  white-space: nowrap;
}
.pill.ok { border-color: #b7e4d4; color: #116149; background: #eaf8f1; }
.pill.warn { border-color: #f1d5a4; color: #8a4b0b; background: #fff7e8; }
.pill.bad { border-color: #f0c4c7; color: #a72c37; background: #fff0f1; }
.pill.demo { border-color: #c9d8ff; color: #244aa5; background: #eef3ff; }

.metric-card {
  background: var(--resq-panel);
  border: 1px solid var(--resq-border);
  border-radius: 14px;
  padding: 17px 18px 15px;
  min-height: 104px;
  box-shadow: var(--resq-shadow);
  transition: box-shadow .18s ease, border-color .18s ease;
}
.metric-card .label {
  color: var(--resq-muted);
  font-size: 11px;
  letter-spacing: .08em;
  font-weight: 700;
  text-transform: uppercase;
}
.metric-card .value {
  font-size: 30px;
  line-height: 1.15;
  font-weight: 700;
  color: var(--resq-ink);
  margin-top: 10px;
  font-family: "IBM Plex Mono", monospace;
}
.metric-card.critical .value { color: var(--resq-red); }
.metric-card.medical .value { color: #b66a12; }
.panel {
  background: #fff;
  border: 1px solid var(--resq-border);
  border-radius: 14px;
  padding: 18px;
  box-shadow: var(--resq-shadow);
  transition: box-shadow .18s ease, border-color .18s ease;
}
.event-line {
  font-family: "IBM Plex Mono", monospace;
  font-size: 12px;
  color: #475569;
  padding: 7px 0;
  border-bottom: 1px solid #edf1f6;
}
.disclaimer {
  color: var(--resq-muted);
  font-size: 12px;
  margin-top: 10px;
}
div[data-testid="stMetric"] {
  background: #fff;
  border: 1px solid var(--resq-border);
  border-radius: 14px;
  padding: 16px 18px;
  box-shadow: var(--resq-shadow);
  transition: border-color .18s ease, box-shadow .18s ease;
}
div[data-testid="stMetricLabel"] p {
  color: var(--resq-muted) !important;
  font-size: 12px;
  font-weight: 600;
}
div[data-testid="stMetricValue"] {
  color: var(--resq-ink);
  font-family: "IBM Plex Mono", monospace;
}
.stDataFrame, [data-testid="stDataFrame"] {
  border: 1px solid var(--resq-border);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(22,34,56,.025);
}
[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--resq-border);
  border-radius: 14px;
}
.stButton > button, [data-testid="stFormSubmitButton"] > button {
  border-radius: 9px;
  font-weight: 600;
  border: 1px solid #d5deeb;
  transition: border-color .15s ease, box-shadow .15s ease, transform .15s ease;
}
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
  border-color: #9db7ee;
  box-shadow: 0 3px 10px rgba(36,87,197,.10);
  transform: translateY(-1px);
}
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] {
  background: var(--resq-blue);
  border-color: var(--resq-blue);
  color: #fff;
}
input, textarea, [data-baseweb="select"] > div {
  border-radius: 10px !important;
}
input:focus, textarea:focus, [data-baseweb="input"]:focus-within, [data-baseweb="select"]:focus-within {
  border-color: #7da0eb !important;
  box-shadow: 0 0 0 3px rgba(36,87,197,.12) !important;
}
[data-testid="stSelectbox"], [data-testid="stTextInput"], [data-testid="stTextArea"], [data-testid="stNumberInput"], [data-testid="stDateInput"] { margin-bottom: .35rem; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { gap: 8px; border-bottom: 1px solid var(--resq-border); }
[data-testid="stTabs"] [data-baseweb="tab"] { padding: 10px 14px; border-radius: 9px 9px 0 0; font-weight: 600; }
[data-testid="stTabs"] [aria-selected="true"] { color: var(--resq-blue) !important; }
[data-testid="stExpander"] { border: 1px solid var(--resq-border); border-radius: 12px; background: var(--resq-panel); }
[data-testid="stExpander"] summary { font-weight: 600; }
[data-testid="stProgressBar"] > div > div { border-radius: 99px; }
[data-testid="stAlert"] p { line-height: 1.55; }
[data-testid="stFileUploader"], [data-testid="stCameraInput"] { border-radius: 12px; }
[data-testid="stSidebarNav"] { padding-top: .35rem; }
[data-testid="stSidebarNav"] a { border-radius: 9px; margin: 2px 6px; transition: background .15s ease; }
[data-testid="stSidebarNav"] a:hover { background: #eef3fb; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background: #eaf0ff; color: #204db0 !important; font-weight: 700; }
button[kind="primary"] { font-weight: 700 !important; }
.stDownloadButton > button { width: 100%; border-radius: 10px; font-weight: 650; }
.stLinkButton > a { border-radius: 9px; font-weight: 600; }
.metric-card:hover, .panel:hover, div[data-testid="stMetric"]:hover { border-color: #ccd8eb; box-shadow: 0 8px 24px rgba(22,34,56,.055); }
[data-testid="stChatMessage"] {
  background: #fff;
  border: 1px solid var(--resq-border);
  border-radius: 14px;
  padding: 14px 16px;
  margin-bottom: 10px;
}
[data-testid="stChatInput"] {
  border-color: #d6dfeb;
  border-radius: 14px;
  background: #fff;
}
[data-testid="stAlert"] {
  border-radius: 12px;
}
hr {
  border-color: var(--resq-border);
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
@media (max-width: 850px) {
  .resq-header { flex-direction: column; }
  .resq-pills { justify-content: flex-start; }
  .resq-title { font-size: 24px; }
}
</style>
"""


DARK_CSS = """
<style>
:root { color-scheme: dark; --resq-ink:#e6edf7; --resq-muted:#a3b1c6; --resq-border:#303d50; --resq-panel:#172234; --resq-canvas:#0d1420; --resq-blue:#8ab4ff; --resq-red:#ff858d; }
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"] { background:var(--resq-canvas)!important; color:var(--resq-ink)!important; }
html,body,[class*="css"],p,label,li,[data-testid="stMarkdownContainer"] { color:var(--resq-ink); }
[data-testid="stHeader"] { background:rgba(13,20,32,.94)!important; }
section[data-testid="stSidebar"] { background:#111b2a!important; border-right-color:var(--resq-border)!important; }
[data-testid="stSidebarNav"] a:hover { background:#202d40!important; }
[data-testid="stSidebarNav"] a[aria-current="page"] { background:#243653!important; color:#c5d9ff!important; font-weight:700; }
[data-testid="stTabs"] [data-baseweb="tab-list"] { border-bottom-color:var(--resq-border); }
[data-testid="stTabs"] [aria-selected="true"] { color:#9fc2ff!important; }
[data-testid="stExpander"] { background:var(--resq-panel)!important; border-color:var(--resq-border)!important; }
.metric-card:hover, .panel:hover, div[data-testid="stMetric"]:hover { border-color:#435775!important; box-shadow:none!important; }
input:focus,textarea:focus,[data-baseweb="input"]:focus-within,[data-baseweb="select"]:focus-within { border-color:#8ab4ff!important; box-shadow:0 0 0 3px rgba(138,180,255,.14)!important; }
h1,h2,h3,h4,h5,.resq-title,.metric-card .value,div[data-testid="stMetricValue"] { color:var(--resq-ink)!important; }
small,.stCaption,[data-testid="stCaptionContainer"],.resq-sub,.disclaimer { color:var(--resq-muted)!important; }
a { color:#9fc2ff!important; }
.metric-card,.panel,div[data-testid="stMetric"],[data-testid="stChatMessage"],[data-testid="stChatInput"],[data-testid="stVerticalBlockBorderWrapper"] { background:var(--resq-panel)!important; border-color:var(--resq-border)!important; color:var(--resq-ink)!important; box-shadow:none!important; }
.event-line { color:#c4d0e0; border-bottom-color:var(--resq-border); }
.pill { background:#202d40; color:#dbe7f7; border-color:#394b63; }
.pill.ok { background:#123a34; color:#9de7cb; border-color:#286b5b; }
.pill.warn { background:#3b2c18; color:#ffd28a; border-color:#755327; }
.pill.bad { background:#3e2029; color:#ffadb4; border-color:#7d3947; }
.pill.demo { background:#1d2d4b; color:#b9d0ff; border-color:#3b5786; }
div[data-testid="stMetricLabel"] p { color:var(--resq-muted)!important; }
.stDataFrame,[data-testid="stDataFrame"] { border-color:var(--resq-border)!important; }
.stButton>button,[data-testid="stFormSubmitButton"]>button { background:#202d40; color:var(--resq-ink); border-color:#40516a; }
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"]>button[kind="primary"] { background:#315fb7; border-color:#4778d2; color:#fff; }
input,textarea,[data-baseweb="select"]>div,[data-baseweb="input"]>div,[data-baseweb="textarea"]>div { background:#172234!important; color:var(--resq-ink)!important; border-color:#40516a!important; }
input::placeholder,textarea::placeholder { color:#91a0b5!important; }
[data-baseweb="popover"],[data-baseweb="menu"],[role="listbox"],[data-baseweb="option"] { background:#172234!important; color:var(--resq-ink)!important; }
[data-baseweb="option"]:hover { background:#263750!important; }
[data-testid="stAlert"] { background:#172234; border-color:var(--resq-border); }
hr { border-color:var(--resq-border)!important; }
</style>
"""


def inject_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    if st.session_state.get("resq_theme", "Light") == "Dark":
        st.markdown(DARK_CSS, unsafe_allow_html=True)


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
    st.sidebar.selectbox("Appearance", ["Light", "Dark"], key="resq_theme", help="Switch the command center between light and dark themes.")
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
