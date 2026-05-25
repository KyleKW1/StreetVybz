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

.stApp { background:var(--bg) !important; }
section[data-testid="stMain"] { background:var(--bg) !important; }
section.main .block-container { padding-bottom: 3rem !important; }

/* Sidebar */
section[data-testid="stSidebar"] {
  background:#0d0d10 !important;
  border-right:1px solid var(--border) !important;
}
section[data-testid="stSidebar"] * { color:#c8c8d8 !important; }
section[data-testid="stSidebar"] .stButton > button {
  background:transparent !important;
  border:1px solid var(--border) !important;
  color:#c8c8d8 !important;
  border-radius:4px !important;
  font-family:'Space Mono',monospace !important;
  font-size:11px !important;
  letter-spacing:1px !important;
  text-transform:uppercase !important;
  transition:all 0.2s !important;
  text-align:left !important;
}
section[data-testid="stSidebar"] .stButton > button:hover {
  background:#1a1a20 !important;
  border-color:var(--lime) !important;
  color:var(--lime) !important;
  box-shadow:none !important;
  transform:none !important;
}

/* Global buttons */
.stButton > button {
  background:var(--card) !important;
  color:var(--text) !important;
  border:1px solid var(--border) !important;
  border-radius:3px !important;
  font-family:'Space Mono',monospace !important;
  font-size:10px !important;
  letter-spacing:1.5px !important;
  text-transform:uppercase !important;
  transition:all 0.15s !important;
  box-shadow:none !important;
}
.stButton > button:hover {
  border-color:var(--lime) !important;
  color:var(--lime) !important;
  box-shadow:none !important;
  transform:none !important;
}
.stButton > button[kind="primary"] {
  background:var(--lime) !important;
  color:#0a0a0b !important;
  border-color:var(--lime) !important;
  font-weight:700 !important;
}
.stButton > button[kind="primary"]:hover {
  background:#d4ff1a !important;
  box-shadow:0 0 20px rgba(198,255,0,0.2) !important;
}

/* Inputs */
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
  background:var(--card) !important;
  border:1px solid var(--border) !important;
  border-radius:3px !important;
  color:var(--text) !important;
  font-family:'DM Sans',sans-serif !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
  border-color:var(--lime) !important;
  box-shadow:0 0 0 2px rgba(198,255,0,0.12) !important;
}
.stTextInput label, .stNumberInput label {
  font-family:'Space Mono',monospace !important;
  font-size:9px !important;
  letter-spacing:2px !important;
  text-transform:uppercase !important;
  color:var(--muted) !important;
}

/* Select boxes */
.stSelectbox > div > div {
  background:var(--card) !important;
  border:1px solid var(--border) !important;
  border-radius:3px !important;
  color:var(--text) !important;
}
.stSelectbox label {
  font-family:'Space Mono',monospace !important;
  font-size:9px !important;
  letter-spacing:2px !important;
  text-transform:uppercase !important;
  color:var(--muted) !important;
}

/* Alerts */
.stAlert {
  border-radius:3px !important;
  font-family:'DM Sans',sans-serif !important;
  font-size:13px !important;
}

/* Progress */
.stProgress > div > div > div { background:var(--lime) !important; }

/* Scrollbar */
::-webkit-scrollbar { width:6px; }
::-webkit-scrollbar-track { background:var(--bg); }
::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:var(--muted); }

#MainMenu { visibility:hidden; }
footer    { visibility:hidden; }
</style>
"""


def apply_custom_styles():
    """
    Inject base CSS. Safe to call multiple times per render —
    only actually writes to the DOM once per Streamlit rerun.
    """
    # Guard: skip if already injected this rerun.
    # We use a flag in session_state tied to Streamlit's internal script run counter,
    # which increments by 1 on every rerun for the session.
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        run_key = f"_css_run_{id(ctx)}" if ctx else "_css_run_fallback"
    except Exception:
        run_key = "_css_run_fallback"

    if st.session_state.get(run_key):
        return

    # Mark as injected for this run, clean up stale keys from prior runs
    stale = [k for k in list(st.session_state.keys())
             if k.startswith("_css_run_") and k != run_key]
    for k in stale:
        del st.session_state[k]
    st.session_state[run_key] = True

    st.html(_BASE_CSS)


def inject_page_css():
    """Alias used by individual pages — same deduplication guard applies."""
    apply_custom_styles()
