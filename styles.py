# styles.py — ViceVault base styles
# CSS is injected at most once per Streamlit rerun.
# Call apply_custom_styles() / inject_page_css() as many times as you like —
# only the first call in each render cycle actually writes to the DOM.

import streamlit as st

_BASE_CSS = """
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400&family=Bebas+Neue&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root {
  --bg:#0a0a0b; --surface:#111114; --card:#18181d;
  --border:#2a2a35; --lime:#c6ff00; --magenta:#ff2d78;
  --cyan:#00e5ff; --amber:#ffb300;
  --text:#f0f0f5; --muted:#5a5a72; --soft:#9090aa;
}

* { box-sizing: border-box; }

/* ── App background ───────────────────────────────────────────── */
.stApp,
.stApp > div,
section[data-testid="stMain"],
section[data-testid="stMain"] > div,
.main,
.main > div,
div[data-testid="stAppViewContainer"],
div[data-testid="stAppViewContainer"] > section {
  background: var(--bg) !important;
  color: var(--text) !important;
}

section.main .block-container {
  padding-bottom: 3rem !important;
  max-width: 860px;
}

/* ── Sidebar ──────────────────────────────────────────────────── */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div {
  background: #0d0d10 !important;
  border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * {
  color: #c8c8d8 !important;
}
section[data-testid="stSidebar"] .stButton > button {
  background: transparent !important;
  border: 1px solid var(--border) !important;
  color: #c8c8d8 !important;
  border-radius: 4px !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 11px !important;
  letter-spacing: 1px !important;
  text-transform: uppercase !important;
  transition: all 0.2s !important;
  text-align: left !important;
  box-shadow: none !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background: #1a1a20 !important;
  border-color: var(--lime) !important;
  color: var(--lime) !important;
  box-shadow: none !important;
  transform: none !important;
}
/* Active sidebar item (primary type) */
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  background: #1a1a20 !important;
  border-color: var(--lime) !important;
  color: var(--lime) !important;
  font-weight: 700 !important;
}

/* ── Global buttons — must beat Streamlit's theme ────────────── */
.stButton > button,
button[kind="secondary"],
button[data-testid="baseButton-secondary"] {
  background: var(--card) !important;
  color: var(--soft) !important;
  border: 1px solid var(--border) !important;
  border-radius: 3px !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 10px !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  transition: all 0.15s !important;
  box-shadow: none !important;
}
.stButton > button:hover {
  border-color: var(--lime) !important;
  color: var(--lime) !important;
  box-shadow: none !important;
  transform: none !important;
}

/* Primary buttons — lime, always */
.stButton > button[kind="primary"],
button[kind="primary"],
button[data-testid="baseButton-primary"] {
  background: var(--lime) !important;
  color: #0a0a0b !important;
  border: 1px solid var(--lime) !important;
  border-radius: 3px !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 10px !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  font-weight: 700 !important;
  box-shadow: none !important;
}
.stButton > button[kind="primary"]:hover {
  background: #d4ff1a !important;
  border-color: #d4ff1a !important;
  color: #0a0a0b !important;
  box-shadow: 0 0 20px rgba(198,255,0,0.2) !important;
  transform: none !important;
}
.stButton > button[kind="primary"]:disabled,
.stButton > button[kind="primary"][disabled] {
  background: var(--border) !important;
  color: var(--muted) !important;
  border-color: var(--border) !important;
  opacity: 0.5 !important;
}

/* ── Inputs ───────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea,
input[type="text"],
input[type="password"],
textarea {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 3px !important;
  color: var(--text) !important;
  font-family: 'DM Sans', sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
  border-color: var(--lime) !important;
  box-shadow: 0 0 0 2px rgba(198,255,0,0.12) !important;
}
.stTextInput label,
.stNumberInput label,
.stTextArea label,
.stSelectbox label,
.stSlider label,
.stRadio label,
.stDateInput label,
.stTimeInput label {
  font-family: 'Space Mono', monospace !important;
  font-size: 9px !important;
  letter-spacing: 2px !important;
  text-transform: uppercase !important;
  color: var(--muted) !important;
}

/* ── Select / Dropdown ────────────────────────────────────────── */
.stSelectbox > div > div,
.stSelectbox > div > div > div {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 3px !important;
  color: var(--text) !important;
}
div[data-baseweb="select"] > div {
  background: var(--card) !important;
  border-color: var(--border) !important;
  color: var(--text) !important;
}

/* ── Radio buttons ────────────────────────────────────────────── */
div[data-testid="stRadio"] > div > label {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 3px !important;
  color: var(--soft) !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 10px !important;
}
div[data-testid="stRadio"] > div > label[data-checked="true"] {
  background: var(--lime) !important;
  border-color: var(--lime) !important;
  color: #0a0a0b !important;
}

/* ── Expander ─────────────────────────────────────────────────── */
details[data-testid="stExpander"],
div[data-testid="stExpander"] {
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 3px !important;
}
details summary,
div[data-testid="stExpander"] summary {
  color: var(--soft) !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 10px !important;
  letter-spacing: 1px !important;
  text-transform: uppercase !important;
}

/* ── Toggle ───────────────────────────────────────────────────── */
div[data-testid="stToggle"] label {
  color: var(--soft) !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px !important;
}

/* ── Alerts / info boxes ──────────────────────────────────────── */
.stAlert,
div[data-testid="stAlert"] {
  border-radius: 3px !important;
  font-family: 'DM Sans', sans-serif !important;
  font-size: 13px !important;
  background: var(--card) !important;
  border: 1px solid var(--border) !important;
  color: var(--soft) !important;
}

/* ── Progress bar ─────────────────────────────────────────────── */
.stProgress > div > div > div,
div[data-testid="stProgressBar"] > div {
  background: var(--lime) !important;
}
.stProgress > div > div {
  background: var(--border) !important;
}

/* ── Toast ────────────────────────────────────────────────────── */
div[data-testid="stToast"] {
  background: var(--card) !important;
  border: 1px solid var(--lime) !important;
  color: var(--text) !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 10px !important;
}

/* ── Download button ──────────────────────────────────────────── */
.stDownloadButton > button {
  background: transparent !important;
  color: var(--soft) !important;
  border: 1px solid var(--border) !important;
  border-radius: 3px !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 10px !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
}
.stDownloadButton > button:hover {
  border-color: var(--lime) !important;
  color: var(--lime) !important;
}

/* ── Markdown / text ──────────────────────────────────────────── */
.stMarkdown, .stMarkdown p,
div[data-testid="stMarkdownContainer"] p {
  color: var(--soft) !important;
  font-family: 'DM Sans', sans-serif !important;
}

/* ── Scrollbar ────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted); }

/* ── Hide Streamlit chrome ────────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }

/* ── Number input stepper buttons ────────────────────────────── */
.stNumberInput button {
  background: var(--card) !important;
  border-color: var(--border) !important;
  color: var(--muted) !important;
}
</style>
"""


def apply_custom_styles():
    """
    Inject base CSS. Safe to call multiple times per render —
    only actually writes to the DOM once per Streamlit rerun.

    Uses a simple boolean flag in session_state rather than ctx id,
    which was unreliable and caused the UI to skip between themes.
    """
    if not st.session_state.get("_vv_css_injected"):
        st.session_state["_vv_css_injected"] = True
        st.html(_BASE_CSS)


def inject_page_css():
    """Alias used by individual pages — same deduplication guard applies."""
    apply_custom_styles()


def reset_css_flag():
    """
    Call this at the very top of main() so CSS re-injects on every full rerun.
    Without this, navigating between pages would skip the CSS after the first render.
    """
    st.session_state["_vv_css_injected"] = False
