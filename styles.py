# styles.py — Hidden base styles
# CSS is injected at most once per Streamlit rerun.
# Call apply_custom_styles() / inject_page_css() as many times as you like —
# only the first call in each render cycle actually writes to the DOM.
#
# Most widget styling (colours, radius, font) now comes from the theme in
# .streamlit/config.toml. This file only covers what the theme can't.

import streamlit as st

_BASE_CSS = """
<style>
@import url("https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,100..900;1,62..125,100..900&display=swap");
:root {
  /* Hidden: after dark. Black for night use, warm whites, and two lights:
     sodium (tonight / your move) and red bulb (desire / the quiz). */
  --night:#000000; --surface:#0f0d0b; --card:#16130f; --raised:#1e1a16; --line:#2b2724;
  --ink:#f2ece4; --smoke:#a79f95; --dim:#8a8178;
  --sodium:#ff9f2e; --bulb:#e8435a;
  --font:'Archivo', system-ui, -apple-system, 'Segoe UI', sans-serif;

  /* Old names, still used by inline styles across the pages */
  --bg:var(--night); --border:var(--line); --text:var(--ink); --soft:var(--smoke); --muted:var(--dim);
  --lime:var(--sodium); --amber:var(--sodium); --magenta:var(--bulb); --cyan:var(--smoke);

  --radius: 14px;
  --radius-sm: 10px;
  --radius-lg: 20px;
}

* { box-sizing: border-box; }

.stApp, .stApp button, .stApp input, .stApp textarea, .stMarkdown, .stMarkdown p {
  font-family: var(--font) !important;
}
.stApp { background: var(--night) !important; color: var(--ink) !important; }
section.main .block-container { padding-bottom: 3rem !important; }

/* ── Buttons: sentence case, no glow ───────────────────────────── */
.stButton button, .stDownloadButton button, .stFormSubmitButton button {
  font-weight: 600 !important; font-size: 15px !important; letter-spacing: 0 !important;
  text-transform: none !important; box-shadow: none !important;
  min-height: 46px; transition: background-color .15s, border-color .15s, color .15s !important;
}
.stButton button[kind="secondary"], .stDownloadButton button, .stFormSubmitButton button {
  background: transparent !important; color: var(--ink) !important; border: 1px solid var(--line) !important;
}
.stButton button[kind="secondary"] *, .stDownloadButton button *, .stFormSubmitButton button * {
  color: inherit !important;
}
.stButton button[kind="secondary"]:hover, .stDownloadButton button:hover,
.stFormSubmitButton button:hover { border-color: var(--smoke) !important; color: var(--ink) !important; }
.stButton button[kind="primary"] {
  background: var(--sodium) !important; border-color: var(--sodium) !important; color: #000 !important;
}
.stButton button[kind="primary"] * { color: #000 !important; }
.stButton button[kind="primary"]:hover { background: #ffb257 !important; border-color: #ffb257 !important; }
.stButton button:disabled { opacity: .5 !important; }
.stButton button[kind="primary"]:disabled { opacity: 1 !important; background: var(--raised) !important;
  border-color: var(--raised) !important; }
.stButton button[kind="primary"]:disabled * { color: var(--dim) !important; }
.stButton button:focus-visible { outline: 2px solid var(--sodium) !important; outline-offset: 2px !important; }

/* ── Inputs ───────────────────────────────────────────────────── */
.stTextInput input, .stTextArea textarea, .stNumberInput input {
  font-size: 16px !important;   /* 16px stops iOS zooming into the field */
}
[data-testid="stWidgetLabel"] p { font-size: 14px !important; color: var(--smoke) !important; font-weight: 500 !important; }

/* ── Markdown / captions ──────────────────────────────────────── */
.stMarkdown p, div[data-testid="stMarkdownContainer"] p { color: var(--smoke); }
div[data-testid="stCaptionContainer"], .stCaption { color: var(--dim) !important; font-size: 13px !important; }

/* ── Alerts: quiet, no coloured slabs ─────────────────────────── */
div[data-testid="stAlert"] > div { background: var(--card) !important; border: 1px solid var(--line) !important; }
div[data-testid="stAlert"] p { color: var(--ink) !important; }

/* ── Toast ────────────────────────────────────────────────────── */
div[data-testid="stToast"] { background: var(--raised) !important; border: 1px solid var(--line) !important;
  color: var(--ink) !important; font-size: 14px !important; }

/* ── Expander ─────────────────────────────────────────────────── */
div[data-testid="stExpander"] details { border-color: var(--line) !important; }
div[data-testid="stExpander"] summary p { color: var(--smoke) !important; font-size: 14px !important; }

/* ── Scrollbar ────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--night); }
::-webkit-scrollbar-thumb { background: var(--line); border-radius: 99px; }

/* ── Hide Streamlit chrome ────────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
</style>
"""


def apply_custom_styles():
    """
    Inject base CSS. Safe to call multiple times per render —
    only actually writes to the DOM once per Streamlit rerun.
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
