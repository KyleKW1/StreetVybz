# styles.py — ViceVault rebrand base styles

import streamlit as st


def inject_page_css():
    """Alias used by individual pages — applies the same global styles."""
    apply_custom_styles()


def apply_custom_styles():
    st.html("""
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
section.main .block-container {
  padding-bottom: 3rem !important;
}

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
""")
